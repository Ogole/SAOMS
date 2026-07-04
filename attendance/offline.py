"""
Offline Attendance Sync Module
Handles offline data storage and synchronization when internet is restored
"""
import json
import time
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
import hashlib
import os


class OfflineStorage:
    """Local storage for offline attendance data"""
    
    def __init__(self):
        self.storage_path = os.path.join(settings.BASE_DIR, 'offline_data')
        self.pending_sync_path = os.path.join(self.storage_path, 'pending_sync')
        os.makedirs(self.pending_sync_path, exist_ok=True)
    
    def save_attendance(self, attendance_data):
        """
        Save attendance record locally for later sync
        attendance_data: dict with attendance information
        """
        try:
            # Create unique ID for the record
            record_id = hashlib.sha256(
                f"{attendance_data.get('officer_id')}_{attendance_data.get('timestamp')}_{time.time()}".encode()
            ).hexdigest()[:16]
            
            # Add metadata
            attendance_data['offline_id'] = record_id
            attendance_data['created_offline'] = True
            attendance_data['sync_attempts'] = 0
            attendance_data['last_sync_attempt'] = None
            
            # Save to local JSON file
            file_path = os.path.join(self.pending_sync_path, f'{record_id}.json')
            with open(file_path, 'w') as f:
                json.dump(attendance_data, f, indent=2)
            
            # Also save to IndexedDB-like structure (browser)
            self._save_to_local_index(record_id, attendance_data)
            
            return {
                'success': True,
                'offline_id': record_id,
                'message': 'Attendance saved offline. Will sync when connected.'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _save_to_local_index(self, record_id, data):
        """Save to local index for quick lookup"""
        index_path = os.path.join(self.storage_path, 'offline_index.json')
        
        index_data = {}
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                index_data = json.load(f)
        
        index_data[record_id] = {
            'officer_id': data.get('officer_id'),
            'timestamp': data.get('timestamp'),
            'type': data.get('type'),
            'synced': False
        }
        
        with open(index_path, 'w') as f:
            json.dump(index_data, f, indent=2)
    
    def get_pending_syncs(self):
        """Get all records pending synchronization"""
        pending_records = []
        
        index_path = os.path.join(self.storage_path, 'offline_index.json')
        if not os.path.exists(index_path):
            return pending_records
        
        with open(index_path, 'r') as f:
            index_data = json.load(f)
        
        for record_id, meta in index_data.items():
            if not meta.get('synced', False):
                record_path = os.path.join(self.pending_sync_path, f'{record_id}.json')
                if os.path.exists(record_path):
                    with open(record_path, 'r') as f:
                        record_data = json.load(f)
                    pending_records.append(record_data)
        
        return pending_records
    
    def sync_with_server(self):
        """
        Synchronize offline records with server
        Called when internet connection is restored
        """
        pending_records = self.get_pending_syncs()
        results = {
            'total': len(pending_records),
            'synced': 0,
            'failed': 0,
            'errors': []
        }
        
        for record in pending_records:
            try:
                # Attempt to sync with Django models
                success = self._sync_single_record(record)
                
                if success:
                    self._mark_as_synced(record['offline_id'])
                    results['synced'] += 1
                else:
                    results['failed'] += 1
                    record['sync_attempts'] += 1
                    record['last_sync_attempt'] = str(timezone.now())
                    
                    # Update the local file with sync attempt info
                    file_path = os.path.join(
                        self.pending_sync_path, 
                        f"{record['offline_id']}.json"
                    )
                    with open(file_path, 'w') as f:
                        json.dump(record, f, indent=2)
                        
                    # If too many attempts, mark as failed permanently
                    if record['sync_attempts'] >= 5:
                        self._move_to_failed(record['offline_id'])
                        
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'offline_id': record.get('offline_id'),
                    'error': str(e)
                })
        
        return results
    
    def _sync_single_record(self, record):
        """Sync individual record to server"""
        try:
            from attendance.models import Attendance
            from core.models import Profile
            
            # Get profile
            profile = Profile.objects.get(id=record['officer_id'])
            
            # Create attendance record
            attendance, created = Attendance.objects.update_or_create(
                profile=profile,
                date=record['date'],
                defaults={
                    'check_in_time': record.get('check_in_time'),
                    'check_out_time': record.get('check_out_time'),
                    'status': record.get('status', 'PRESENT'),
                    'check_in_method': record.get('method', 'OFFLINE'),
                    'remarks': f"Synced from offline record. Original: {record.get('timestamp')}"
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Sync error for {record.get('offline_id')}: {str(e)}")
            return False
    
    def _mark_as_synced(self, record_id):
        """Mark record as successfully synced"""
        index_path = os.path.join(self.storage_path, 'offline_index.json')
        
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                index_data = json.load(f)
            
            if record_id in index_data:
                index_data[record_id]['synced'] = True
                index_data[record_id]['synced_at'] = str(timezone.now())
            
            with open(index_path, 'w') as f:
                json.dump(index_data, f, indent=2)
    
    def _move_to_failed(self, record_id):
        """Move record to failed folder after max attempts"""
        failed_path = os.path.join(self.storage_path, 'failed_syncs')
        os.makedirs(failed_path, exist_ok=True)
        
        source = os.path.join(self.pending_sync_path, f'{record_id}.json')
        dest = os.path.join(failed_path, f'{record_id}.json')
        
        if os.path.exists(source):
            os.rename(source, dest)
    
    def get_sync_status(self):
        """Get overall sync status"""
        pending = len(self.get_pending_syncs())
        
        index_path = os.path.join(self.storage_path, 'offline_index.json')
        total = 0
        synced = 0
        
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                index_data = json.load(f)
                total = len(index_data)
                synced = sum(1 for v in index_data.values() if v.get('synced', False))
        
        return {
            'total_records': total,
            'synced_records': synced,
            'pending_sync': pending,
            'last_sync': self._get_last_sync_time()
        }
    
    def _get_last_sync_time(self):
        """Get timestamp of last successful sync"""
        sync_log = os.path.join(self.storage_path, 'sync_log.json')
        if os.path.exists(sync_log):
            with open(sync_log, 'r') as f:
                log = json.load(f)
                return log.get('last_sync')
        return None
    
    def clear_synced_records(self, days_old=7):
        """Clear synced records older than specified days"""
        cutoff = timezone.now() - timedelta(days=days_old)
        
        index_path = os.path.join(self.storage_path, 'offline_index.json')
        if not os.path.exists(index_path):
            return
        
        with open(index_path, 'r') as f:
            index_data = json.load(f)
        
        to_remove = []
        for record_id, meta in index_data.items():
            if meta.get('synced') and meta.get('synced_at'):
                synced_at = timezone.datetime.fromisoformat(meta['synced_at'])
                if synced_at < cutoff:
                    to_remove.append(record_id)
                    # Remove the file
                    file_path = os.path.join(self.pending_sync_path, f'{record_id}.json')
                    if os.path.exists(file_path):
                        os.remove(file_path)
        
        # Update index
        for record_id in to_remove:
            del index_data[record_id]
        
        with open(index_path, 'w') as f:
            json.dump(index_data, f, indent=2)


# Service Worker registration script for browser
SERVICE_WORKER_JS = """
// Service Worker for offline functionality
const CACHE_NAME = 'upf-attendance-v1';
const OFFLINE_URL = '/attendance/offline/';

const urlsToCache = [
    '/',
    '/static/css/bootstrap.min.css',
    '/static/js/attendance-offline.js',
    OFFLINE_URL,
];

// Install Service Worker
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(urlsToCache))
    );
});

// Fetch strategy: Network first, fallback to cache
self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request)
            .catch(() => {
                return caches.match(event.request);
            })
    );
});

// Background sync for offline attendance
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-attendance') {
        event.waitUntil(syncAttendanceData());
    }
});

async function syncAttendanceData() {
    const db = await openDatabase();
    const pendingRecords = await getPendingRecords(db);
    
    for (const record of pendingRecords) {
        try {
            const response = await fetch('/api/attendance/sync/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(record)
            });
            
            if (response.ok) {
                await markAsSynced(db, record.id);
            }
        } catch (error) {
            console.error('Sync failed:', error);
        }
    }
}

function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('UPFAttendance', 1);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('pendingAttendance')) {
                db.createObjectStore('pendingAttendance', {keyPath: 'id'});
            }
        };
        
        request.onsuccess = (event) => resolve(event.target.result);
        request.onerror = (event) => reject(event.target.error);
    });
}
"""
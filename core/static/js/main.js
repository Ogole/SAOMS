// fingerprint_scanner.js
// This handles communication with actual fingerprint scanner hardware

class FingerprintScanner {
    constructor() {
        this.deviceType = null;
        this.isScanning = false;
        this.scanner = null;
    }
    
    // Initialize scanner based on type
    async initialize(deviceType) {
        this.deviceType = deviceType;
        
        switch(deviceType) {
            case 'USB':
                return await this.initUSBScanner();
            case 'BLUETOOTH':
                return await this.initBluetoothScanner();
            case 'MOBILE':
                return await this.initMobileScanner();
            case 'BUILTIN':
                return await this.initBuiltinScanner();
            default:
                throw new Error('Unknown scanner type');
        }
    }
    
    // USB Scanner (e.g., DigitalPersona, SecuGen)
    async initUSBScanner() {
        try {
            // Using WebUSB API or manufacturer SDK
            const device = await navigator.usb.requestDevice({
                filters: [{ vendorId: 0x1234 }] // Replace with actual vendor ID
            });
            
            await device.open();
            await device.selectConfiguration(1);
            await device.claimInterface(0);
            
            this.scanner = device;
            return true;
        } catch (error) {
            console.error('USB scanner initialization failed:', error);
            throw error;
        }
    }
    
    // Bluetooth Scanner (e.g., Futronic, Mantra)
    async initBluetoothScanner() {
        try {
            const device = await navigator.bluetooth.requestDevice({
                filters: [{ services: ['fingerprint_service_uuid'] }], // Replace with actual service
                optionalServices: []
            });
            
            const server = await device.gatt.connect();
            const service = await server.getPrimaryService('fingerprint_service_uuid');
            
            this.scanner = { device, server, service };
            return true;
        } catch (error) {
            console.error('Bluetooth scanner initialization failed:', error);
            throw error;
        }
    }
    
    // Mobile Device Scanner (Android/iOS biometric API)
    async initMobileScanner() {
        // Check if platform supports biometric authentication
        if (!window.PublicKeyCredential) {
            throw new Error('WebAuthn not supported');
        }
        
        // Platform authenticator for fingerprint
        const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
        
        if (!available) {
            throw new Error('No platform authenticator available');
        }
        
        return true;
    }
    
    // Built-in laptop scanner
    async initBuiltinScanner() {
        // Some laptops have built-in fingerprint readers
        // Use platform-specific APIs
        return await this.initMobileScanner(); // Similar to mobile
    }
    
    // Scan fingerprint
    async scanFingerprint(fingerPosition = 'any') {
        if (this.isScanning) {
            throw new Error('Scan already in progress');
        }
        
        this.isScanning = true;
        
        try {
            let template;
            
            switch(this.deviceType) {
                case 'USB':
                    template = await this.scanUSB(fingerPosition);
                    break;
                case 'BLUETOOTH':
                    template = await this.scanBluetooth(fingerPosition);
                    break;
                case 'MOBILE':
                    template = await this.scanMobile(fingerPosition);
                    break;
                case 'BUILTIN':
                    template = await this.scanBuiltin(fingerPosition);
                    break;
            }
            
            // Convert template to base64 for transmission
            const base64Template = btoa(String.fromCharCode(...new Uint8Array(template)));
            
            return {
                success: true,
                template: base64Template,
                quality: this.calculateQuality(template),
                fingerPosition: fingerPosition
            };
            
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        } finally {
            this.isScanning = false;
        }
    }
    
    // USB scanner communication
    async scanUSB(fingerPosition) {
        // Send scan command to USB device
        const scanCommand = new Uint8Array([0x01, 0x02, 0x03]); // Example command
        
        if (this.scanner && this.scanner.transferOut) {
            await this.scanner.transferOut(1, scanCommand);
            
            // Read result
            const result = await this.scanner.transferIn(1, 1024);
            return new Uint8Array(result.data.buffer);
        }
        
        throw new Error('USB scanner not initialized');
    }
    
    // Bluetooth scanner communication
    async scanBluetooth(fingerPosition) {
        if (this.scanner && this.scanner.service) {
            const characteristic = await this.scanner.service.getCharacteristic(
                'fingerprint_characteristic_uuid'
            );
            
            // Write scan command
            await characteristic.writeValue(new Uint8Array([0x01]));
            
            // Wait for notification with template
            return new Promise((resolve, reject) => {
                characteristic.addEventListener('characteristicvaluechanged', (event) => {
                    resolve(new Uint8Array(event.target.value.buffer));
                });
                
                setTimeout(() => reject(new Error('Timeout')), 30000);
            });
        }
        
        throw new Error('Bluetooth scanner not initialized');
    }
    
    // Mobile fingerprint scan (Android/iOS)
    async scanMobile(fingerPosition) {
        const publicKey = {
            challenge: new Uint8Array(32),
            rp: { name: "UPF Attendance System" },
            user: {
                id: new Uint8Array(16),
                name: "officer@upf.go.ug",
                displayName: "Officer"
            },
            pubKeyCredParams: [{ type: "public-key", alg: -7 }],
            authenticatorSelection: {
                authenticatorAttachment: "platform",
                userVerification: "required"
            },
            timeout: 60000,
            attestation: "direct"
        };
        
        try {
            const credential = await navigator.credentials.create({ publicKey });
            
            // Extract fingerprint data from credential
            const response = credential.response;
            const authenticatorData = response.attestationObject;
            
            return new Uint8Array(authenticatorData);
        } catch (error) {
            throw new Error('Fingerprint scan failed or cancelled');
        }
    }
    
    // Built-in scanner
    async scanBuiltin(fingerPosition) {
        // Similar to mobile for platform authenticators
        return await this.scanMobile(fingerPosition);
    }
    
    // Calculate fingerprint quality
    calculateQuality(template) {
        // Simple quality estimation based on template size and variance
        if (!template || template.length < 100) {
            return 0;
        }
        
        let quality = 0;
        
        // Check template size (typical good templates are 500-1000 bytes)
        if (template.length > 500) quality += 40;
        else if (template.length > 250) quality += 20;
        
        // Check for data variance (not all zeros or repeating patterns)
        let variance = 0;
        const mean = template.reduce((a, b) => a + b, 0) / template.length;
        variance = template.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / template.length;
        
        if (variance > 1000) quality += 40;
        else if (variance > 500) quality += 20;
        
        // Additional checks
        if (template.length > 700) quality += 20;
        
        return Math.min(quality, 100);
    }
    
    // Capture multiple fingerprints
    async captureAllFingers() {
        const fingers = {
            'right_thumb': null,
            'right_index': null,
            'left_thumb': null,
            'left_index': null
        };
        
        for (let finger in fingers) {
            console.log(`Please place ${finger.replace('_', ' ')}...`);
            
            // Wait a moment for user to place finger
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            const result = await this.scanFingerprint(finger);
            if (result.success) {
                fingers[finger] = {
                    template: result.template,
                    quality: result.quality
                };
            }
        }
        
        return fingers;
    }
    
    // Disconnect scanner
    async disconnect() {
        if (this.scanner) {
            if (this.deviceType === 'USB' && this.scanner.close) {
                await this.scanner.close();
            } else if (this.deviceType === 'BLUETOOTH' && this.scanner.device) {
                await this.scanner.device.gatt.disconnect();
            }
            this.scanner = null;
        }
    }
}

// Usage in your template:
const fpScanner = new FingerprintScanner();

async function registerFingerprint() {
    try {
        // Get selected device type
        const deviceType = document.getElementById('fingerprintDevice').value;
        
        // Initialize scanner
        await fpScanner.initialize(deviceType);
        
        // Update UI
        document.getElementById('scanStatus').textContent = 'Place finger on scanner...';
        document.getElementById('scanProgress').style.width = '0%';
        
        // Animate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 5;
            document.getElementById('scanProgress').style.width = progress + '%';
            if (progress >= 90) clearInterval(progressInterval);
        }, 500);
        
        // Scan fingerprint
        const result = await fpScanner.scanFingerprint();
        
        clearInterval(progressInterval);
        
        if (result.success) {
            // Fill hidden form fields
            document.getElementById('fingerprintData').value = result.template;
            document.getElementById('fingerprintQuality').value = result.quality;
            
            // Update UI
            document.getElementById('scanProgress').style.width = '100%';
            document.getElementById('scanStatus').textContent = 
                `✓ Fingerprint captured successfully! (Quality: ${result.quality}%)`;
            document.getElementById('scanStatus').style.color = 'green';
            
            // Show preview if available
            if (result.template) {
                document.getElementById('fingerprintPreview').innerHTML = 
                    '<i class="bi bi-fingerprint" style="font-size: 48px; color: green;"></i>';
            }
            
            // Enable submit button
            document.getElementById('submitBiometric').disabled = false;
            
        } else {
            document.getElementById('scanStatus').textContent = 
                `✗ Scan failed: ${result.error}`;
            document.getElementById('scanStatus').style.color = 'red';
            document.getElementById('scanProgress').style.width = '0%';
        }
        
    } catch (error) {
        console.error('Fingerprint registration error:', error);
        document.getElementById('scanStatus').textContent = 
            `Error: ${error.message}`;
        document.getElementById('scanStatus').style.color = 'red';
    }
}

// Register multiple fingers
async function registerAllFingers() {
    try {
        const deviceType = document.getElementById('fingerprintDevice').value;
        await fpScanner.initialize(deviceType);
        
        const allFingers = await fpScanner.captureAllFingers();
        
        // Store each finger's template
        if (allFingers.right_thumb) {
            document.getElementById('fingerprintThumb').value = allFingers.right_thumb.template;
        }
        if (allFingers.right_index) {
            document.getElementById('fingerprintIndex').value = allFingers.right_index.template;
        }
        
        console.log('All fingers captured:', allFingers);
        
    } catch (error) {
        console.error('Multi-finger capture error:', error);
    }
}
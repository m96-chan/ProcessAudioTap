import Foundation
import CoreAudio
import AudioToolbox
import AVFoundation

// Private Core Audio APIs
@_silgen_name("AudioHardwareCreateProcessTap")
func AudioHardwareCreateProcessTap(_ tapDescription: AnyObject, _ outTapID: UnsafeMutablePointer<AudioObjectID>) -> OSStatus

@_silgen_name("AudioHardwareDestroyProcessTap")
func AudioHardwareDestroyProcessTap(_ tapID: AudioObjectID) -> OSStatus

@available(macOS 14.2, *)
func requestMicrophonePermission() -> Bool {
    fputs("Requesting microphone permission...\n", stderr)

    let semaphore = DispatchSemaphore(value: 0)
    var granted = false

    AVCaptureDevice.requestAccess(for: .audio) { result in
        granted = result
        if result {
            fputs("Microphone permission granted\n", stderr)
        } else {
            fputs("Microphone permission denied\n", stderr)
        }
        semaphore.signal()
    }

    // Wait for permission response (with timeout)
    let timeout = DispatchTime.now() + .seconds(60)
    let result = semaphore.wait(timeout: timeout)

    if result == .timedOut {
        fputs("WARNING: Permission request timed out\n", stderr)
        return false
    }

    return granted
}

@available(macOS 14.2, *)
func checkScreenRecordingPermission() -> Bool {
    // Screen Recording permission is required to access other processes' audio
    // We check this by attempting to get the list of windows
    let windowList = CGWindowListCopyWindowInfo([.optionOnScreenOnly], kCGNullWindowID) as? [[String: Any]]

    if let windows = windowList, windows.count > 0 {
        fputs("Screen Recording permission: Granted\n", stderr)
        return true
    } else {
        fputs("ERROR: Screen Recording permission required\n", stderr)
        fputs("Please grant Screen Recording access in System Settings > Privacy & Security > Screen Recording\n", stderr)
        fputs("This permission is needed to access audio from other processes.\n", stderr)
        return false
    }
}

@available(macOS 14.2, *)
func checkMicrophonePermission() -> Bool {
    let status = AVCaptureDevice.authorizationStatus(for: .audio)

    switch status {
    case .authorized:
        fputs("Microphone permission: Already authorized\n", stderr)
        return true
    case .notDetermined:
        fputs("Microphone permission: Not determined, requesting...\n", stderr)
        return requestMicrophonePermission()
    case .denied:
        fputs("ERROR: Microphone permission denied\n", stderr)
        fputs("Please grant microphone access in System Settings > Privacy & Security > Microphone\n", stderr)
        return false
    case .restricted:
        fputs("ERROR: Microphone access is restricted\n", stderr)
        return false
    @unknown default:
        fputs("WARNING: Unknown microphone permission status\n", stderr)
        return false
    }
}

@available(macOS 14.2, *)
func checkAllPermissions() -> Bool {
    var allGranted = true

    // Check microphone permission
    if !checkMicrophonePermission() {
        allGranted = false
    }

    // Check screen recording permission (needed for process audio access)
    if !checkScreenRecordingPermission() {
        allGranted = false
    }

    return allGranted
}

@available(macOS 14.2, *)
func findProcessAudioObject(pid: pid_t) -> AudioObjectID? {
    // Use kAudioHardwarePropertyTranslatePIDToProcessObject (direct API)
    // This is what AudioCap uses - it's a direct translation API
    var propertyAddress = AudioObjectPropertyAddress(
        mSelector: AudioObjectPropertySelector(0x70696432),  // 'pid2' = kAudioHardwarePropertyTranslatePIDToProcessObject
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )

    var processObjectID: AudioObjectID = 0
    var dataSize = UInt32(MemoryLayout<AudioObjectID>.size)
    var qualifierData = pid
    let qualifierSize = UInt32(MemoryLayout<pid_t>.size)

    let status = AudioObjectGetPropertyData(
        AudioObjectID(kAudioObjectSystemObject),
        &propertyAddress,
        qualifierSize,
        &qualifierData,
        &dataSize,
        &processObjectID
    )

    if status == noErr && processObjectID != 0 {
        fputs("Found process object ID \(processObjectID) for PID \(pid)\n", stderr)
        return processObjectID
    } else {
        fputs("ERROR: Failed to translate PID \(pid) to process object (status=\(status), objectID=\(processObjectID))\n", stderr)
        return nil
    }
}

@available(macOS 14.2, *)
@main
struct ProcTapHelper {
    static func main() {
        let args = CommandLine.arguments

        guard args.count >= 2 else {
            fputs("Usage: proctap-helper <PID>\n", stderr)
            exit(1)
        }

        guard let pid = pid_t(args[1]) else {
            fputs("Error: Invalid PID\n", stderr)
            exit(1)
        }

        fputs("ProcTap Helper starting for PID \(pid)\n", stderr)

        // Check and request all required permissions
        if !checkAllPermissions() {
            fputs("Error: Required permissions not granted\n", stderr)
            exit(1)
        }

        guard let processObjectID = findProcessAudioObject(pid: pid) else {
            fputs("Error: Process \(pid) has no audio\n", stderr)
            exit(1)
        }

        fputs("Found process audio object: \(processObjectID)\n", stderr)

        // Use Objective-C runtime to create CATapDescription
        guard let catClass = objc_getClass("CATapDescription") as? NSObject.Type else {
            fputs("Error: CATapDescription class not found\n", stderr)
            exit(1)
        }

        let processArray = [NSNumber(value: processObjectID)] as NSArray

        // Use unsafeBitCast to call Objective-C methods
        typealias InitMethod = @convention(c) (AnyObject, Selector, NSArray) -> AnyObject
        let initSelector = NSSelectorFromString("initStereoMixdownOfProcesses:")
        let allocSelector = NSSelectorFromString("alloc")

        let allocMethod = unsafeBitCast(
            class_getClassMethod(catClass, allocSelector),
            to: (@convention(c) (AnyObject, Selector) -> AnyObject).self
        )

        let tapDescObj = allocMethod(catClass, allocSelector)

        let initMethod = unsafeBitCast(
            class_getInstanceMethod(catClass, initSelector),
            to: InitMethod.self
        )

        let tapDescription = initMethod(tapDescObj, initSelector, processArray)

        // Set UUID
        let tapUUID = UUID()
        let nsuuid = NSUUID(uuidString: tapUUID.uuidString)!

        let setUUIDSelector = NSSelectorFromString("setUUID:")
        tapDescription.perform(setUUIDSelector, with: nsuuid)

        fputs("Created tap description\n", stderr)

        // Create Process Tap
        var tapDeviceID: AudioObjectID = 0
        var status = AudioHardwareCreateProcessTap(tapDescription, &tapDeviceID)

        guard status == noErr, tapDeviceID != 0 else {
            fputs("Error: Failed to create Process Tap (status=\(status))\n", stderr)
            exit(1)
        }

        fputs("Process Tap created: device ID \(tapDeviceID)\n", stderr)

        // Get default output device
        var defaultOutputPropertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultOutputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        var defaultOutputID: AudioObjectID = 0
        var outputSize = UInt32(MemoryLayout<AudioObjectID>.size)

        status = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &defaultOutputPropertyAddress,
            0, nil,
            &outputSize,
            &defaultOutputID
        )

        guard status == noErr else {
            fputs("Error: Failed to get default output device\n", stderr)
            AudioHardwareDestroyProcessTap(tapDeviceID)
            exit(1)
        }

        // Get output device UID
        var uidPropertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyDeviceUID,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        var outputUID: Unmanaged<CFString>?
        var uidSize = UInt32(MemoryLayout<CFString>.size)

        status = AudioObjectGetPropertyData(
            defaultOutputID,
            &uidPropertyAddress,
            0, nil,
            &uidSize,
            &outputUID
        )

        let outputUIDString: String
        if status == noErr, let uid = outputUID?.takeUnretainedValue() as String? {
            outputUIDString = uid
        } else {
            outputUIDString = "BuiltInSpeakerDevice"
        }

        // Create Aggregate Device
        let aggregateUID = UUID().uuidString

        let description: [String: Any] = [
            "name": "ProcTap-\(pid)",
            "uid": aggregateUID,
            "private": true,
            "stacked": false,
            "autostart": true,
            "master": outputUIDString,
            "subdevices": [
                ["uid": outputUIDString]
            ],
            "taps": [
                [
                    "drift": true,
                    "uid": tapUUID.uuidString
                ]
            ]
        ]

        var aggregateDeviceID: AudioObjectID = 0
        status = AudioHardwareCreateAggregateDevice(description as CFDictionary, &aggregateDeviceID)

        guard status == noErr, aggregateDeviceID != 0 else {
            fputs("Error: Failed to create Aggregate Device (status=\(status))\n", stderr)
            AudioHardwareDestroyProcessTap(tapDeviceID)
            exit(1)
        }

        fputs("Aggregate Device created\n", stderr)

        // Create IOProc with block
        let queue = DispatchQueue(label: "com.proctap.ioproc", qos: .userInitiated)

        var ioProcID: AudioDeviceIOProcID?

        status = AudioDeviceCreateIOProcIDWithBlock(
            &ioProcID,
            aggregateDeviceID,
            queue
        ) { (now, inputData, inputTime, outputData, outputTime) in
            guard inputData.pointee.mNumberBuffers > 0 else { return }

            let buffer = inputData.pointee.mBuffers
            guard let data = buffer.mData else { return }
            let size = Int(buffer.mDataByteSize)

            let bytePtr = data.bindMemory(to: UInt8.self, capacity: size)
            let bufferPointer = UnsafeBufferPointer(start: bytePtr, count: size)

            FileHandle.standardOutput.write(Data(bufferPointer))
        }

        guard status == noErr, let procID = ioProcID else {
            fputs("Error: Failed to create IOProc (status=\(status))\n", stderr)
            AudioHardwareDestroyAggregateDevice(aggregateDeviceID)
            AudioHardwareDestroyProcessTap(tapDeviceID)
            exit(1)
        }

        // Start device
        status = AudioDeviceStart(aggregateDeviceID, procID)

        guard status == noErr else {
            fputs("Error: Failed to start device (status=\(status))\n", stderr)
            AudioDeviceDestroyIOProcID(aggregateDeviceID, procID)
            AudioHardwareDestroyAggregateDevice(aggregateDeviceID)
            AudioHardwareDestroyProcessTap(tapDeviceID)
            exit(1)
        }

        fputs("Ready\n", stderr)

        // Run forever
        // Note: Signal handling is managed by parent process
        RunLoop.main.run()
    }
}

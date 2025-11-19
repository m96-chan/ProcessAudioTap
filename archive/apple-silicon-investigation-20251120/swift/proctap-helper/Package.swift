// swift-tools-version: 6.1
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "proctap-helper",
    platforms: [
        .macOS(.v14)  // macOS 14.2+ required for Process Tap API
    ],
    targets: [
        // Targets are the basic building blocks of a package, defining a module or a test suite.
        // Targets can depend on other targets in this package and products from dependencies.
        .executableTarget(
            name: "proctap-helper",
            linkerSettings: [
                .linkedFramework("AVFoundation")
            ]
        ),
    ]
)

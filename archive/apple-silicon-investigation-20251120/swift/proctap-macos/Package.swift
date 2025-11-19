// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "proctap-macos",
    platforms: [
        .macOS(.v14)  // Requires macOS 14.4+ for Process Tap API
    ],
    products: [
        .executable(
            name: "proctap-macos",
            targets: ["proctap-macos"]
        )
    ],
    targets: [
        .executableTarget(
            name: "proctap-macos",
            dependencies: [],
            path: "Sources"
        )
    ]
)

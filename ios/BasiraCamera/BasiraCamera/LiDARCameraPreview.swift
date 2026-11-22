import ARKit
import Combine
import SceneKit
import SwiftUI

@MainActor
final class DepthReader: ObservableObject {
    @Published private(set) var distanceMeters: Float?
    @Published private(set) var confidence: ARConfidenceLevel?
    @Published private(set) var isAvailable = false
    @Published private(set) var message = "Preparing rear camera and depth sensor"

    var distanceText: String {
        guard let distanceMeters else { return "—" }
        return String(format: "%.2f m", distanceMeters)
    }

    var confidenceText: String {
        switch confidence {
        case .high: return "High"
        case .medium: return "Medium"
        case .low: return "Low"
        case nil: return "Waiting"
        @unknown default: return "Unknown"
        }
    }

    var statusText: String {
        if let distanceMeters {
            switch distanceMeters {
            case ..<0.8: return "Very near obstacle"
            case ..<1.5: return "Obstacle nearby"
            default: return "Path distance measured"
            }
        }
        return message
    }

    var statusColor: Color {
        guard let distanceMeters else { return .yellow }
        switch distanceMeters {
        case ..<0.8: return .red
        case ..<1.5: return .orange
        default: return .green
        }
    }

    func setUnavailable(_ message: String) {
        isAvailable = false
        self.message = message
    }

    func update(distance: Float, confidence: ARConfidenceLevel) {
        // A short moving average removes single-frame LiDAR noise.
        if let previous = distanceMeters {
            distanceMeters = previous * 0.7 + distance * 0.3
        } else {
            distanceMeters = distance
        }
        self.confidence = confidence
        isAvailable = true
    }
}

struct LiDARCameraPreview: UIViewRepresentable {
    @ObservedObject var depthReader: DepthReader
    @ObservedObject var liveClient: LiveAnalysisClient

    func makeCoordinator() -> Coordinator {
        Coordinator(depthReader: depthReader, liveClient: liveClient)
    }

    func makeUIView(context: Context) -> ARSCNView {
        let view = ARSCNView(frame: .zero)
        view.session.delegate = context.coordinator
        view.automaticallyUpdatesLighting = true
        context.coordinator.start(on: view.session)
        return view
    }

    func updateUIView(_ uiView: ARSCNView, context: Context) {}

    static func dismantleUIView(_ uiView: ARSCNView, coordinator: Coordinator) {
        uiView.session.pause()
    }

    final class Coordinator: NSObject, ARSessionDelegate {
        private let depthReader: DepthReader
        private let liveClient: LiveAnalysisClient

        init(depthReader: DepthReader, liveClient: LiveAnalysisClient) {
            self.depthReader = depthReader
            self.liveClient = liveClient
        }

        func start(on session: ARSession) {
            guard ARWorldTrackingConfiguration.isSupported else {
                depthReader.setUnavailable("World tracking is unavailable on this device")
                return
            }

            guard ARWorldTrackingConfiguration.supportsFrameSemantics(.smoothedSceneDepth) else {
                depthReader.setUnavailable("LiDAR scene depth is unavailable on this device")
                return
            }

            let configuration = ARWorldTrackingConfiguration()
            configuration.frameSemantics.insert(.smoothedSceneDepth)
            configuration.frameSemantics.insert(.sceneDepth)
            session.run(configuration, options: [.resetTracking, .removeExistingAnchors])
        }

        func session(_ session: ARSession, didUpdate frame: ARFrame) {
            guard let depthData = frame.smoothedSceneDepth ?? frame.sceneDepth,
                  let sample = centerDepthSample(from: depthData) else { return }

            Task { @MainActor in
                depthReader.update(distance: sample.distance, confidence: sample.confidence)
                liveClient.submit(frame: frame)
            }
        }

        private func centerDepthSample(from depthData: ARDepthData) -> (distance: Float, confidence: ARConfidenceLevel)? {
            let depthMap = depthData.depthMap
            guard let confidenceMap = depthData.confidenceMap else { return nil }
            CVPixelBufferLockBaseAddress(depthMap, .readOnly)
            CVPixelBufferLockBaseAddress(confidenceMap, .readOnly)
            defer {
                CVPixelBufferUnlockBaseAddress(depthMap, .readOnly)
                CVPixelBufferUnlockBaseAddress(confidenceMap, .readOnly)
            }

            guard let depthBase = CVPixelBufferGetBaseAddress(depthMap),
                  let confidenceBase = CVPixelBufferGetBaseAddress(confidenceMap) else { return nil }

            let width = CVPixelBufferGetWidth(depthMap)
            let height = CVPixelBufferGetHeight(depthMap)
            let depthStride = CVPixelBufferGetBytesPerRow(depthMap) / MemoryLayout<Float32>.stride
            let confidenceStride = CVPixelBufferGetBytesPerRow(confidenceMap)
            let centerX = width / 2
            let centerY = height / 2
            let depth = depthBase.assumingMemoryBound(to: Float32.self)
            let confidence = confidenceBase.assumingMemoryBound(to: UInt8.self)

            var values: [Float] = []
            var bestConfidence: ARConfidenceLevel = .low
            for y in max(0, centerY - 3)...min(height - 1, centerY + 3) {
                for x in max(0, centerX - 3)...min(width - 1, centerX + 3) {
                    let value = depth[y * depthStride + x]
                    let rawConfidence = confidence[y * confidenceStride + x]
                    guard value.isFinite, value > 0.1, value < 8.0,
                          let level = ARConfidenceLevel(rawValue: Int(rawConfidence)) else { continue }
                    values.append(value)
                    if level.rawValue > bestConfidence.rawValue { bestConfidence = level }
                }
            }

            guard !values.isEmpty else { return nil }
            values.sort()
            return (values[values.count / 2], bestConfidence)
        }
    }
}

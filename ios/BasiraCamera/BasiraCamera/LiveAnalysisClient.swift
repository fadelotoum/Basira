import ARKit
import Combine
import CoreImage
import Foundation
import UIKit

struct RemoteObject: Decodable, Identifiable {
    let label: String
    let confidence: Double
    let bbox: NormalizedBox

    var id: String { "\(label)-\(bbox.x)-\(bbox.y)" }
}

struct NormalizedBox: Decodable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

private struct AnalysisRequest: Encodable {
    let frameID: Int
    let jpegBase64: String

    enum CodingKeys: String, CodingKey {
        case frameID = "frame_id"
        case jpegBase64 = "jpeg_base64"
    }
}

private struct AnalysisResponse: Decodable {
    let type: String
    let frameID: Int?
    let objects: [RemoteObject]?
    let message: String?

    enum CodingKeys: String, CodingKey {
        case type, objects, message
        case frameID = "frame_id"
    }
}

@MainActor
final class LiveAnalysisClient: NSObject, ObservableObject, NetServiceBrowserDelegate, NetServiceDelegate {
    enum ConnectionState: Equatable {
        case idle
        case discovering
        case connected
        case failed(String)
    }

    @Published private(set) var state: ConnectionState = .idle
    @Published private(set) var objects: [RemoteObject] = []

    private var socket: URLSessionWebSocketTask?
    private let serviceBrowser = NetServiceBrowser()
    private var discoveredService: NetService?
    private var nextFrameID = 0
    private var lastSubmission = Date.distantPast
    private let ciContext = CIContext(options: [.cacheIntermediates: false])

    var statusLabel: String {
        switch state {
        case .idle: return "Mac AI offline"
        case .discovering: return "Finding Basira Mac"
        case .connected: return "Mac AI live"
        case .failed: return "Mac AI unavailable"
        }
    }

    override init() {
        super.init()
        serviceBrowser.delegate = self
    }

    func discoverMac() {
        disconnect()
        state = .discovering
        serviceBrowser.searchForServices(ofType: "_basira._tcp.", inDomain: "local.")
    }

    private func connect(to url: URL) {
        serviceBrowser.stop()

        let task = URLSession.shared.webSocketTask(with: url)
        socket = task
        task.resume()
        state = .connected
        receiveNext()
    }

    func disconnect() {
        serviceBrowser.stop()
        discoveredService?.stop()
        discoveredService = nil
        socket?.cancel(with: .goingAway, reason: nil)
        socket = nil
        objects = []
        state = .idle
    }

    func netServiceBrowser(_ browser: NetServiceBrowser, didFind service: NetService, moreComing: Bool) {
        guard discoveredService == nil else { return }
        discoveredService = service
        service.delegate = self
        service.resolve(withTimeout: 5)
    }

    func netServiceDidResolveAddress(_ sender: NetService) {
        guard let host = sender.hostName,
              let url = URL(string: "ws://\(host):\(sender.port)/ws/frames") else {
            state = .failed("Basira Mac could not be reached")
            return
        }
        connect(to: url)
    }

    func netService(_ sender: NetService, didNotResolve errorDict: [String: NSNumber]) {
        state = .failed("Basira Mac could not be reached")
    }

    func submit(frame: ARFrame) {
        guard socket != nil,
              Date().timeIntervalSince(lastSubmission) >= 0.35 else { return }
        lastSubmission = Date()
        nextFrameID += 1

        guard let jpegData = makeJPEG(from: frame.capturedImage) else { return }
        let request = AnalysisRequest(frameID: nextFrameID, jpegBase64: jpegData.base64EncodedString())

        do {
            let data = try JSONEncoder().encode(request)
            guard let text = String(data: data, encoding: .utf8) else { return }
            socket?.send(.string(text)) { [weak self] error in
                guard let error else { return }
                Task { @MainActor in self?.state = .failed(error.localizedDescription) }
            }
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    private func receiveNext() {
        socket?.receive { [weak self] result in
            Task { @MainActor in
                guard let self else { return }
                switch result {
                case .success(.string(let text)):
                    self.handleResponse(text)
                case .success:
                    break
                case .failure(let error):
                    self.state = .failed(error.localizedDescription)
                    return
                }
                self.receiveNext()
            }
        }
    }

    private func handleResponse(_ text: String) {
        guard let data = text.data(using: .utf8),
              let response = try? JSONDecoder().decode(AnalysisResponse.self, from: data) else { return }

        if response.type == "analysis" {
            objects = response.objects ?? []
        } else if response.type == "error" {
            state = .failed(response.message ?? "The Mac could not analyse this frame")
        }
    }

    private func makeJPEG(from pixelBuffer: CVPixelBuffer) -> Data? {
        // Keep the raw camera orientation so the frame and LiDAR map stay aligned.
        let image = CIImage(cvPixelBuffer: pixelBuffer)
        guard let cgImage = ciContext.createCGImage(image, from: image.extent) else { return nil }

        let source = UIImage(cgImage: cgImage)
        let maxWidth: CGFloat = 640
        let scale = min(maxWidth / source.size.width, 1)
        let size = CGSize(width: source.size.width * scale, height: source.size.height * scale)
        let renderer = UIGraphicsImageRenderer(size: size)
        let reduced = renderer.image { _ in source.draw(in: CGRect(origin: .zero, size: size)) }
        return reduced.jpegData(compressionQuality: 0.55)
    }
}

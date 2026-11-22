import SwiftUI
import Combine

struct ContentView: View {
    @StateObject private var session = AppSession()

    var body: some View {
        Group {
            if session.hasStarted {
                BasiraLiveView()
            } else {
                BasiraWelcomeView { session.hasStarted = true }
            }
        }
        .preferredColorScheme(.dark)
    }
}

private final class AppSession: ObservableObject {
    @Published var hasStarted = false
}

private struct BasiraWelcomeView: View {
    let start: () -> Void

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color(red: 0.015, green: 0.04, blue: 0.10), Color(red: 0.02, green: 0.17, blue: 0.30)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 22) {
                Spacer()

                Image("BrandMark")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 148, height: 148)
                    .clipShape(RoundedRectangle(cornerRadius: 34, style: .continuous))
                    .shadow(color: .cyan.opacity(0.26), radius: 28, y: 12)

                VStack(spacing: 8) {
                    Text("BASIRA")
                        .font(.system(size: 40, weight: .bold, design: .rounded))
                        .tracking(2)
                    Text("AI obstacle awareness for visual independence")
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.72))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 34)
                }

                HStack(spacing: 10) {
                    WelcomeFeature(icon: "dot.radiowaves.left.and.right", label: "LiDAR distance")
                    WelcomeFeature(icon: "cpu", label: "Local AI")
                    WelcomeFeature(icon: "bolt.fill", label: "Live")
                }
                .padding(.top, 6)

                Spacer()

                Button(action: start) {
                    HStack(spacing: 10) {
                        Text("Start Basira")
                        Image(systemName: "arrow.right")
                    }
                    .font(.headline.weight(.bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 18)
                }
                .buttonStyle(.borderedProminent)
                .tint(.cyan)
                .foregroundStyle(.black)

                Text("A prototype for obstacle awareness. Use a mobility aid and stay attentive to your surroundings.")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.48))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 18)
            }
            .padding(24)
        }
    }
}

private struct WelcomeFeature: View {
    let icon: String
    let label: String

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
                .foregroundStyle(.cyan)
            Text(label)
        }
        .font(.caption.weight(.medium))
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(.white.opacity(0.10), in: Capsule())
    }
}

private struct BasiraLiveView: View {
    @StateObject private var depthReader = DepthReader()
    @StateObject private var liveClient = LiveAnalysisClient()

    var body: some View {
        ZStack {
            LiDARCameraPreview(depthReader: depthReader, liveClient: liveClient)
                .ignoresSafeArea()

            LinearGradient(
                colors: [.black.opacity(0.75), .clear, .black.opacity(0.8)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
            .allowsHitTesting(false)

            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    HStack(spacing: 10) {
                        Image("BrandMark")
                            .resizable()
                            .scaledToFit()
                            .frame(width: 46, height: 46)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

                        VStack(alignment: .leading, spacing: 3) {
                            Text("BASIRA")
                                .font(.system(size: 25, weight: .bold, design: .rounded))
                                .tracking(1)
                            Text("Live spatial awareness")
                                .font(.subheadline)
                                .foregroundStyle(.white.opacity(0.75))
                        }
                    }

                    Spacer()

                    Label(depthReader.isAvailable ? "LiDAR live" : "Starting", systemImage: "dot.radiowaves.left.and.right")
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(.white.opacity(0.16), in: Capsule())
                }

                Spacer()

                if !liveClient.objects.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("MAC AI DETECTS")
                            .font(.caption2.weight(.bold))
                            .foregroundStyle(.white.opacity(0.6))
                        ForEach(liveClient.objects.prefix(3)) { object in
                            HStack {
                                Image(systemName: "viewfinder")
                                    .foregroundStyle(.cyan)
                                Text(object.label.capitalized)
                                    .font(.subheadline.weight(.semibold))
                                Spacer()
                                Text("\(Int(object.confidence * 100))%")
                                    .font(.caption.weight(.bold))
                                    .foregroundStyle(.white.opacity(0.65))
                            }
                        }
                    }
                    .padding(14)
                    .background(.black.opacity(0.42), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text(depthReader.distanceText)
                        .font(.system(size: 48, weight: .bold, design: .rounded))

                    Text(depthReader.statusText)
                        .font(.headline)
                        .foregroundStyle(depthReader.statusColor)

                    HStack(spacing: 12) {
                        Metric(title: "Confidence", value: depthReader.confidenceText)
                        Metric(title: "Source", value: "LiDAR")
                        Metric(title: "Mac AI", value: liveClient.statusLabel)
                    }

                    Button(liveClient.state == .connected ? "Disconnect Mac AI" : "Connect Mac AI") {
                        if liveClient.state == .connected {
                            liveClient.disconnect()
                        } else {
                            liveClient.discoverMac()
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(liveClient.state == .connected ? .orange : .blue)

                    if !liveClient.objects.isEmpty {
                        Text("Mac sees: " + liveClient.objects.prefix(3).map(\.label).joined(separator: ", "))
                            .font(.subheadline.weight(.semibold))
                            .lineLimit(1)
                    }
                }
                .padding(20)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
            }
            .padding(20)
            .foregroundStyle(.white)
        }
    }
}

private struct Metric: View {
    let title: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title.uppercased())
                .font(.caption2.weight(.bold))
                .foregroundStyle(.white.opacity(0.62))
            Text(value)
                .font(.subheadline.weight(.semibold))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 9)
        .background(.white.opacity(0.12), in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}


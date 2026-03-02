import Foundation

/// Network client for the NeuroArousal FastAPI backend.
@MainActor
class APIClient: ObservableObject {
    @Published var baseURL: String = "http://localhost:7860"
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let session: URLSession
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
    }

    // MARK: - Scenarios

    func listScenarios() async throws -> [String] {
        return try await get("/scenarios")
    }

    func getScenarioInfo(_ name: String) async throws -> ScenarioInfoOut {
        return try await get("/scenarios/\(name)")
    }

    // MARK: - Simulation

    func runScenario(_ name: String, adapter: String = "default") async throws -> SimulationOut {
        return try await post("/run/scenario/\(name)?adapter=\(adapter)", body: Optional<String>.none)
    }

    func runCustom(_ request: CustomRunRequest) async throws -> SimulationOut {
        return try await post("/run/custom", body: request)
    }

    // MARK: - State Inspector

    func getState(step: Int? = nil) async throws -> StateSnapshot {
        if let step = step {
            return try await get("/state/\(step)")
        }
        return try await get("/state")
    }

    // MARK: - Alignment & Arc

    func getAlignment() async throws -> AlignmentOut {
        return try await get("/alignment")
    }

    func getArc() async throws -> NarrativeArcOut {
        return try await get("/arc")
    }

    // MARK: - Nullclines

    func getNullclines(somaA: Double = 0.25, somaB: Double = 0.5,
                       psycheA: Double = 0.20, psycheB: Double = 0.45) async throws -> NullclineOut {
        return try await get("/nullclines?soma_a=\(somaA)&soma_b=\(somaB)&psyche_a=\(psycheA)&psyche_b=\(psycheB)")
    }

    // MARK: - Adapters

    func listAdapters() async throws -> [AdapterOut] {
        return try await get("/adapters")
    }

    func setAdapter(_ name: String) async throws {
        let _: [String: String] = try await post("/adapters/\(name)", body: Optional<String>.none)
    }

    // MARK: - Character

    func getCharacterAppearance(step: Int? = nil) async throws -> CharacterAppearance {
        var path = "/character/appearance"
        if let step = step { path += "?step=\(step)" }
        return try await get(path)
    }

    func getCharacterImage(step: Int? = nil) async throws -> Data {
        var path = "/character/image"
        if let step = step { path += "?step=\(step)" }

        guard let url = URL(string: baseURL + path) else {
            throw APIError.invalidURL
        }
        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            throw APIError.serverError("HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0)")
        }
        return data
    }

    // MARK: - Generic Helpers

    private func get<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.invalidURL
        }
        isLoading = true
        defer { isLoading = false }

        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw APIError.serverError("HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0): \(body)")
        }
        return try decoder.decode(T.self, from: data)
    }

    private func post<T: Decodable, B: Encodable>(_ path: String, body: B?) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.invalidURL
        }
        isLoading = true
        defer { isLoading = false }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let body = body {
            request.httpBody = try encoder.encode(body)
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw APIError.serverError("HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0): \(body)")
        }
        return try decoder.decode(T.self, from: data)
    }
}

enum APIError: LocalizedError {
    case invalidURL
    case serverError(String)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Invalid server URL"
        case .serverError(let msg): return msg
        }
    }
}

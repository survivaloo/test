//
//  ExchangeRateViewModel.swift
//  USDJPYRate
//
//  Frankfurter API (https://www.frankfurter.app) を利用して
//  USD/JPY のレートを取得するビューモデル。APIキーは不要。
//

import Foundation

struct ExchangeRateResponse: Decodable {
    let amount: Double
    let base: String
    let date: String
    let rates: [String: Double]
}

@MainActor
final class ExchangeRateViewModel: ObservableObject {
    @Published private(set) var rate: Double?
    @Published private(set) var lastUpdated: String = ""
    @Published private(set) var isLoading: Bool = false
    @Published private(set) var errorMessage: String?

    private let endpoint = URL(string: "https://api.frankfurter.app/latest?from=USD&to=JPY")!
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func fetchRate() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let (data, response) = try await session.data(from: endpoint)

            guard let httpResponse = response as? HTTPURLResponse,
                  (200...299).contains(httpResponse.statusCode) else {
                errorMessage = "サーバーからの応答が正しくありません。"
                return
            }

            let decoded = try JSONDecoder().decode(ExchangeRateResponse.self, from: data)

            guard let jpyRate = decoded.rates["JPY"] else {
                errorMessage = "レート情報が見つかりませんでした。"
                return
            }

            rate = jpyRate
            lastUpdated = decoded.date
        } catch {
            errorMessage = "取得に失敗しました: \(error.localizedDescription)"
        }
    }
}

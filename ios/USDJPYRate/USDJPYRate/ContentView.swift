//
//  ContentView.swift
//  USDJPYRate
//

import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = ExchangeRateViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()

                VStack(spacing: 8) {
                    Text("USD / JPY")
                        .font(.title2)
                        .foregroundStyle(.secondary)

                    if viewModel.isLoading {
                        ProgressView()
                            .scaleEffect(1.5)
                            .padding(.vertical, 24)
                    } else if let rate = viewModel.rate {
                        Text(String(format: "¥%.2f", rate))
                            .font(.system(size: 56, weight: .bold, design: .rounded))
                            .foregroundStyle(.primary)

                        Text("1 米ドル あたり")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    } else {
                        Text("--")
                            .font(.system(size: 56, weight: .bold, design: .rounded))
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(24)
                .frame(maxWidth: .infinity)
                .background(
                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                        .fill(Color(.secondarySystemBackground))
                )
                .padding(.horizontal)
                .animation(.default, value: viewModel.rate)

                if let error = viewModel.errorMessage {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(.red)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }

                if !viewModel.lastUpdated.isEmpty {
                    Text("最終更新日: \(viewModel.lastUpdated)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Button {
                    Task { await viewModel.fetchRate() }
                } label: {
                    Label("更新する", systemImage: "arrow.clockwise")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                }
                .buttonStyle(.borderedProminent)
                .padding(.horizontal)
                .disabled(viewModel.isLoading)
                .padding(.bottom)
            }
            .navigationTitle("ドル円レート")
            .task {
                await viewModel.fetchRate()
            }
            .refreshable {
                await viewModel.fetchRate()
            }
        }
    }
}

#Preview {
    ContentView()
}

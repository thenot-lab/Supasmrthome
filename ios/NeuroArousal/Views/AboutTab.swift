import SwiftUI

struct AboutTab: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("NeuroArousal")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("Coupled Excitable System Exhibit")
                    .font(.title3)
                    .foregroundColor(.secondary)

                Divider()

                SectionHeader("Mathematical Model")
                Text("""
                Two coupled FitzHugh-Nagumo oscillators with sigmoidal delay coupling:

                SOMA (physiological arousal):
                  du1/dt = u1(1-u1)(u1-a1) - v1 + c12*S(u2(t-tau)) + I1(t)
                  dv1/dt = e1*(b1*u1 - v1)

                PSYCHE (cognitive/emotional arousal):
                  du2/dt = u2(1-u2)(u2-a2) - v2 + c21*S(u1(t-tau)) + I2(t)
                  dv2/dt = e2*(b2*u2 - v2)

                where S(x) = 1/(1 + exp(-kappa*(x-theta)))
                """)
                .font(.system(.caption, design: .monospaced))

                Divider()

                SectionHeader("Emotional Drive Mapping")
                InfoRow(left: "E_u (0-100)", right: "Arousal drive -> SOMA boost")
                InfoRow(left: "E_v (0-100)", right: "Valence drive -> PSYCHE shift")
                InfoRow(left: "E_v0 = 0.2", right: "Resting valence baseline")

                Divider()

                SectionHeader("Savage Mode")
                Text("epsilon=0.05, a=0.5, b=0.1, E_v0=0.2, c12=0.35, c21=0.30, kappa=20")
                    .font(.caption).foregroundColor(.secondary)

                Divider()

                SectionHeader("PEFT Adapters")
                ForEach(adapterRows, id: \.0) { name, tone in
                    InfoRow(left: name, right: tone)
                }

                Divider()

                SectionHeader("References")
                Text("""
                - Blyuss, K.B. & Kyrychko, Y.N. (2010). Bull. Math. Biol., 72, 490-505.
                - FitzHugh, R. (1961). Biophys. J., 1(6), 445-466.
                - Nagumo, J. et al. (1962). Proc. IRE, 50(10), 2061-2070.
                """)
                .font(.caption)
                .foregroundColor(.secondary)

                Divider()

                SectionHeader("Server Connection")
                Text("This app connects to the NeuroArousal FastAPI backend. Configure the server URL in Settings (gear icon).")
                    .font(.caption).foregroundColor(.secondary)

                Text("v2.0.0")
                    .font(.caption2)
                    .foregroundColor(.tertiary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.top)
            }
            .padding()
        }
    }

    private var adapterRows: [(String, String)] {
        [
            ("Museum Default", "Measured, educational"),
            ("Poetic Narrator", "Lyrical, metaphorical"),
            ("Clinical Observer", "Precise, technical"),
            ("Dramatic Storyteller", "Vivid, suspenseful"),
        ]
    }
}

struct SectionHeader: View {
    let text: String
    init(_ text: String) { self.text = text }

    var body: some View {
        Text(text)
            .font(.headline)
            .fontWeight(.semibold)
    }
}

struct InfoRow: View {
    let left: String
    let right: String

    var body: some View {
        HStack {
            Text(left)
                .font(.caption)
                .fontWeight(.medium)
                .frame(maxWidth: .infinity, alignment: .leading)
            Text(right)
                .font(.caption)
                .foregroundColor(.secondary)
                .frame(maxWidth: .infinity, alignment: .trailing)
        }
    }
}

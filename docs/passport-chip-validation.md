# Passport chip validation from the client's phone

Written 2026-11-06. Companion to `market-gaps.md`. Firms only.

**How much to trust this.** Compiled from third-party SDK docs, Apple developer-forum posts, ICAO pages and vendor blogs. I did not read Apple's own Core NFC documentation and have not built anything. Items marked *(background)* are from my general knowledge, not from this research. Verify before relying on them.

## 1. The question

Can a firm send its client a link that lets the client's phone read the passport chip, so the firm gets passport data that is cryptographically proven genuine?

## 2. Short answer

- **Yes, iPhones can read passport chips.** The path is Core NFC, available from iOS 13 on iPhone 7 and later. [NFCW](https://www.nfcw.com/?p=62943) confirmed iOS 13 support at launch. Apple itself reads US passport chips for its [Digital ID in Wallet](https://appleinsider.com/articles/25/11/12/passports-on-iphone-arrive-with-new-digital-id-feature) (iOS 26.1, iPhone 11 or later, US passports only).
- **A plain web link cannot do it.** Safari on iOS does not support Web NFC ([caniuse](https://caniuse.com/webnfc); Apple reportedly declined to implement it in 2020 over privacy). Chrome on Android supports Web NFC, but I believe it covers simple NDEF tags and not passport chips *(background; verify)*. A [Universal NFC README](https://unpkg.com/unfc@1.0.3/README.md) states that iPhones can read tags only through a native app built on Core NFC, or a native app's web view with a bridge.
- So the link must **open a native app** (or hand the client to an app-based verification flow). It cannot be a pure web page.

## 3. What reading a passport needs on iOS

- A native app with the NFC Tag Reading capability.
- The passport application identifiers (`A0000002471001` and `A0000002472001`) listed under the ISO 7816 select-identifiers key in `Info.plist`. Forum reports say the read silently fails without it, and that putting these in the entitlements file causes a provisioning error ([Apple forum](https://developer.apple.com/forums/thread/817267)).
- An access key derived from the passport's machine-readable zone (document number, date of birth, expiry). BAC and PACE are the access protocols. A wrong key typically produces a mutual-authentication error.
- A physical iPhone. The simulator cannot emulate NFC *(background)*.
- A reader session that lasts about 60 seconds at most. Reads reportedly take around 10 seconds.
- Open-source starting point: [NFCPassportReader](https://www.GitHub.com/AndyQ/NFCPassportReader) (Swift). It lists BAC, secure messaging, active and passive authentication. Its README lists **PACE as unfinished**, and one fork says only the Generic Mapping variant is supported. Many newer passports use PACE, so this needs checking against the current source and against real passports.
- App Clips (lightweight apps opened from a link): I found nothing confirming they can read passport chips. One developer hit a "Missing required entitlement" error with NFC in an App Clip. **Unknown; check with Apple.**

## 4. Options

| Option | How it works | Pros | Cons |
|---|---|---|---|
| Own native app (iOS, then Android) | Link opens the app (or the store page). Client scans the MRZ with the camera and taps the passport | Full control, nothing sent to a third party | App Store review, two apps to maintain, PACE gaps, needs a trust store |
| App Clip | Link opens a small app without install | Smoother for a one-off | NFC support in App Clips unconfirmed |
| Buy an ID-verification SDK | Vendor handles the read and the check | Fastest; vendors already cover protocol quirks | Passport data goes to a third party; per-verification fees; adds a subprocessor |

Reported per-verification prices (vendor-authored comparison, [Didit](https://updates.didit.me/blog/best-nfc-passport-verification-tools-epassport-reading/)): Onfido about $2-3, Jumio $3-5, Sumsub $1.50-3, PassportReader from $0.10, IdentiGate EUR 0.50-2.00, Inverid GBP 0.50-3.95. Didit claims its NFC verification is free, which I have not verified. Treat all as rough. I found nothing on Veriff or Persona and nothing on how desktop-to-phone handoff is implemented.

## 5. How the verification should work (design)

1. The firm creates a one-time, short-lived verification session. The link carries a random token only. **No personal data in the URL.**
2. The client opens the app, scans the machine-readable zone with the camera (or types the three values), and taps the passport.
3. The phone sends the **raw chip contents** (the security object and data groups) back. It does not send a "passed" flag, because the phone is not trusted.
4. The **verifier** (firm side) does the checking:
   - Verify the security object's signature up to a trusted country certificate (passive authentication).
   - Check each data group's hash against the signed hashes.
   - Optionally send a random challenge, relayed through the phone to the chip, to detect a cloned chip (active authentication).
   - Compare the chip's identity data with what the firm already has.
5. The result is stored in the evidence report as "chip-verified on [date], trust anchor [country certificate]".
6. Read the identity data group only. Avoid reading the photo data group unless needed: it is biometric data, and I have not researched the legal rules for storing or matching it.

## 6. The trust store problem

Verification needs the issuing country's signing certificates.

- ICAO publishes a [Master List](https://www.icao.int/icao-pkd/icao-master-list) free to download. The page I saw lists 547 certificates (March 2026 issue). ICAO's 2022 board report gave 696 certificates from 70 issuing entities; I could not reconcile the counts.
- **The terms restrict use to personal or organizational non-commercial use** ([terms](https://www.icao.int/icao-pkd/icao-master-list-terms-and-conditions)). That matters for a commercial product. Needs legal review.
- ICAO also says the list is not an automatic trust decision: each user sets their own policy.
- Full PKD participation was priced at US$56,000 in a 2008 working paper. Current fees unknown.
- Other states publish their own certificate lists *(background; not verified)*.
- Coverage will be incomplete, so the product needs an honest "could not verify" state for passports from countries it has no certificate for.

## 7. Data flow and the local-first question

A phone cannot talk to a firm's desktop directly. Choices:
- **Hosted portal:** simple, but data touches your servers.
- **Zero-knowledge relay:** the phone encrypts the chip data to the firm's public key, a relay holds only ciphertext until the desktop collects and deletes it. Fits local-first, more to build.
- **Third-party vendor:** simplest, but the passport data goes to them.

This ties directly to the open decision on hosted versus local.

## 8. Limits and risks

- Not all passports have chips, and some older ones cannot be read with the open-source library.
- Android needs a separate app (Chrome Web NFC does not solve it).
- Clients may not know to tap the phone to the passport, so the flow needs clear instructions.
- Passive authentication proves the data was signed by the issuer and is unaltered. It does not prove the person holding the passport is the owner, and it does not detect a cloned chip without active authentication.
- iOS reading conventions and entitlement details come from forum posts. Confirm with Apple's documentation.

## 9. Suggested de-risking steps (no client data involved)

1. Build a tiny iOS test app with NFCPassportReader and read **your own** passport on a physical iPhone. Record read time, whether BAC or PACE was needed, and any errors.
2. Run passive authentication on the result with the ICAO Master List for your passport's country.
3. Test an App Clip build for the NFC entitlement question.
4. Get a lawyer's view on the Master List terms and on photo-data handling before building the trust store.
5. Decide hosted portal, relay or vendor.

## 10. Sources

- NFCW on iOS 13: https://www.nfcw.com/?p=62943
- Apple developer forum (entitlement and AID): https://developer.apple.com/forums/thread/817267
- Apple developer forum (ISO 7816 tags): https://developer.apple.com/forums/thread/117329
- caniuse Web NFC: https://caniuse.com/webnfc
- Universal NFC README: https://unpkg.com/unfc@1.0.3/README.md
- NFCPassportReader: https://www.GitHub.com/AndyQ/NFCPassportReader
- ICAO Master List: https://www.icao.int/icao-pkd/icao-master-list
- ICAO Master List terms: https://www.icao.int/icao-pkd/icao-master-list-terms-and-conditions
- ICAO PKD FAQ: https://www.icao.int/icao-pkd/frequently-asked-questions
- Vendor comparison (Didit blog): https://updates.didit.me/blog/best-nfc-passport-verification-tools-epassport-reading/
- Apple Digital ID (AppleInsider): https://appleinsider.com/articles/25/11/12/passports-on-iphone-arrive-with-new-digital-id-feature

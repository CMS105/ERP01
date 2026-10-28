# Architectural Decisions: LPG ERP Mobile Application

## 1. Stack Selection
- Selected React 18 + Vite + TypeScript mobile-first PWA / Capacitor-ready architecture housed in `android/`.
- Justification: Provides instant hot module reloading, lightweight footprint, cross-platform Android WebView embedding capability, and full compatibility with existing Node/npm setup without heavy external SDK overhead.

## 2. Visual Direction & Design Tokens
- Style: Warm claymorphism with soft neumorphic shadows, rounded geometry (14-24px radius), and tactile inset highlights.
- Palette:
  - Cream Background: `#FBF1E3`
  - Deep Clay Cards: `#F3E2CF`
  - Primary Terracotta: `#B84E2F`
  - Soft Terracotta: `#E9A27A`
  - Accent Marigold: `#F6B93B`
  - Text Primary: `#3A2618`
  - Success Green: `#3F8F5B`
  - Error Red: `#C0392B`

## 3. Role-Based Experiences
- `CUSTOMER`:
  - Quota balance display with subsidy indicators.
  - Cylinder booking with dynamic price computation (14.2kg @ ₹850 - ₹200 subsidy = ₹650).
  - Live 5-step delivery tracking stepper with driver details.
  - Order history and profile address updates.
- `DELIVERY_BOY`:
  - Daily tasks summary metrics (Total, Assigned, Delivered).
  - Search and filter by delivery status.
  - Task details with click-to-call and map navigation directions.
  - Outcome recording with 5 distinct delivery outcome codes and empty cylinder serial logging.
  - Payment collection supporting Cash, UPI QR, and mPOS Bluetooth terminal simulation.

## 4. Offline Queue & Synchronization
- Local storage offline queue stores delivery outcomes and collections when connectivity is lost.
- Generates unique `offline_sync_id` (format: `offline_<timestamp>_<random>`).
- Seamlessly submits batch transactions to `/api/v1/delivery-boy/deliveries/sync-offline` when connection restores.

## 5. Mock Bluetooth mPOS Terminal
- Deterministic 9-state machine: `idle` -> `scanning` -> `deviceFound` -> `connecting` -> `confirmAmount` -> `processing` -> `success` / `failed` / `timeout`.
- Claymorphic modal displays paired terminal `PINELABS-MPOS-8821`, battery status, animated indicators, and live simulation controls.

## 6. Bilingual Localization & Audio Accessibility
- Comprehensive English & Kannada string bundle in `src/i18n/strings.json`.
- Zero-latency language switching without page reload.
- Native Web Speech API / TTS fallback with Kannada locale voice detection for audio playback.
- Pre-generated audio manifest registered at `public/audio/manifest.json`.
- Note: Kannada translations are provided via localized string mapping; a native speaker review is recommended prior to field production deployment.

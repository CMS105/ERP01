# Implementation Plan: LPG Smart ERP Enhancements

## 1. Backend Updates (FastAPI - HACKATHON 2026)
*   **Models (`models.py`)**: Add `SupportTicket` table. Status enum (`PENDING_SYNC`, `OPEN`, `AI_ASSISTED`, `WAITING_FOR_STAFF`, `IN_PROGRESS`, `RESOLVED`). Add `transaction_reference` column to `DeliveryExecution` or use `id` as a unique transaction code.
*   **Schemas (`schemas.py`)**: Add Pydantic schemas for `SupportTicketCreate`, `SupportTicketOut`, `SupportTicketReply`.
*   **AI Integration (`services.py`)**: Add `SupportTicketService`. Integrate `google.generativeai` (Gemini) to process issue text, validate context, and return AI suggestions in English or Kannada.
*   **Routers**: Add `POST /api/v1/customer/tickets` and `GET /api/v1/customer/tickets`.

## 2. Android Data Layer Updates (APPFORLPG)
*   **Room Database**:
    *   Add `SupportTicketEntity` to `Entities.kt`.
    *   Add `SupportTicketDao` to `Daos.kt`.
    *   Update `AppDatabase.kt` version.
*   **API Client (`ApiService.kt`)**: Add `SupportTicketDto`, `SupportTicketRequestDto` and corresponding endpoints.
*   **Repository (`LpgRepository.kt` & `LpgRepositoryImpl.kt`)**:
    *   Implement `raiseIssue()` with offline-first support (saves to Room, adds to `pending_sync_operations`).
    *   Implement `getSupportTicketsFlow()`.
    *   Update `completeDelivery()` to generate a robust `transaction_reference` locally and synchronize it.

## 3. Android UI/UX Updates (APPFORLPG)
*   **Language Persistence**: Use SharedPreferences or DataStore to persist `isKannada` language selection.
*   **Customer Support Screen (`CustomerScreen.kt` & new `SupportScreen.kt`)**:
    *   Add "Raise an Issue" button linking to a form.
    *   Pre-fill booking/delivery references.
    *   Show localized category dropdowns.
    *   Display AI response with "Solved" or "Still need help" buttons.
*   **Delivery Partner Screen**:
    *   Show unique transaction code after delivery completion.

## 4. Testing & Verification
*   Test Room DB migration.
*   Test offline-first issue creation.
*   Test Gemini API interaction (mocked if no key).
*   Test Kannada strings rendering.

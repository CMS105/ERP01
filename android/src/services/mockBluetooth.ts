export type BluetoothState =
  | "idle"
  | "scanning"
  | "deviceFound"
  | "connecting"
  | "confirmAmount"
  | "processing"
  | "success"
  | "failed"
  | "timeout"
  | "bluetoothOff"
  | "permissionDenied";

export interface MockBluetoothPaymentResult {
  success: boolean;
  transactionReference?: string;
  errorMessage?: string;
}

export class MockBluetoothService {
  private listener?: (state: BluetoothState) => void;
  private currentTimeout?: any;

  public subscribe(callback: (state: BluetoothState) => void) {
    this.listener = callback;
  }

  public cancel() {
    if (this.currentTimeout) {
      clearTimeout(this.currentTimeout);
    }
    if (this.listener) {
      this.listener("idle");
    }
  }

  public startPaymentProcess(amount: number, failSimulated: boolean = false) {
    if (!this.listener) return;

    this.listener("scanning");

    this.currentTimeout = setTimeout(() => {
      this.listener!("deviceFound");

      this.currentTimeout = setTimeout(() => {
        this.listener!("connecting");

        this.currentTimeout = setTimeout(() => {
          this.listener!("confirmAmount");

          this.currentTimeout = setTimeout(() => {
            this.listener!("processing");

            this.currentTimeout = setTimeout(() => {
              if (failSimulated) {
                this.listener!("failed");
              } else {
                this.listener!("success");
              }
            }, 1200);
          }, 1000);
        }, 1000);
      }, 1000);
    }, 1200);
  }
}

export const mockBluetooth = new MockBluetoothService();

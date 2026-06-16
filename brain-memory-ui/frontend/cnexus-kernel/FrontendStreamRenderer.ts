/**
 * FrontendStreamRenderer — incremental token rendering for Fast Lane v2.
 */

export type StreamRenderCallback = (token: string, buffer: string) => void;

export class FrontendStreamRenderer {
  buffer = "";

  constructor(private onRender?: StreamRenderCallback) {}

  async onToken(token: string): Promise<void> {
    this.buffer += token;
    this.renderIncremental(token);
  }

  renderIncremental(token: string): void {
    if (this.onRender) {
      this.onRender(token, this.buffer);
      return;
    }
    if (typeof process !== "undefined" && process.stdout?.write) {
      process.stdout.write(token);
    }
  }

  reset(): void {
    this.buffer = "";
  }
}

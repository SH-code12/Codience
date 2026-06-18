import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

export function activate(context: vscode.ExtensionContext) {
  const provider = new SidebarProvider(context.extensionUri);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      SidebarProvider.viewType,
      provider,
    ),
  );
}

export function deactivate() {}

class SidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "sidebarView";

  constructor(private readonly _extensionUri: vscode.Uri) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    const webview = webviewView.webview;

    webview.options = {
      enableScripts: true,
      localResourceRoots: [
        vscode.Uri.joinPath(
          this._extensionUri,
          "webview-ui",
          "webview-ui",
          "dist",
        ),
      ],
    };

    const indexPath = path.join(
      this._extensionUri.fsPath,
      "webview-ui",
      "webview-ui",
      "dist",
      "index.html",
    );

    let html = fs.readFileSync(indexPath, "utf-8");

    html = html.replace(
      /(src|href)="(.+?)"/g,
      (_match: string, attr: string, link: string) => {
        if (/^https?:\/\//.test(link)) {
          return _match;
        }

        const uri = webview.asWebviewUri(
          vscode.Uri.joinPath(
            this._extensionUri,
            "webview-ui",
            "webview-ui",
            "dist",
            link,
          ),
        );

        return `${attr}="${uri}"`;
      },
    );

    // Inject CSP (Content Security Policy)
    html = html.replace(
      "<head>",
      `<head>
    <meta http-equiv="Content-Security-Policy"
      content="
        default-src 'none';
        img-src ${webview.cspSource} https:;
        style-src ${webview.cspSource} 'unsafe-inline';
        script-src ${webview.cspSource};
        connect-src
          https://codience.onrender.com
          https://sphery-arlen-nondecorative.ngrok-free.dev
          https://fordless-samella-unexpendable.ngrok-free.dev
          http://localhost:5051/
          http://localhost:8000/
          http://127.0.0.1:8000/
          http://127.0.0.1:8001/
          http://127.0.0.1:8002/;
          http://127.0.0.1:8003/;
      ">
  `,
    );

    webview.html = html;
  }
}

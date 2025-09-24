import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

export function activate(context: vscode.ExtensionContext) {
  const provider = new SidebarProvider(context.extensionUri);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      SidebarProvider.viewType,
      provider
    )
  );
}

export function deactivate() {}

class SidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "sidebarView";

  constructor(private readonly _extensionUri: vscode.Uri) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    const webview = webviewView.webview;

    webview.options = {
      enableScripts: true,
      localResourceRoots: [
        vscode.Uri.joinPath(
          this._extensionUri,
          "webview-ui",
          "webview-ui",
          "dist"
        ),
      ],
    };

    // Path to your React build's index.html
    const indexPath = path.join(
      this._extensionUri.fsPath,
      "webview-ui",
      "webview-ui",
      "dist",
      "index.html"
    );

    let html = fs.readFileSync(indexPath, "utf-8");

    // Replace local paths (JS/CSS) with vscode webview URIs
    html = html.replace(/(src|href)="(.+?)"/g, (match, attr, link) => {
      if (/^https?:\/\//.test(link)) {
        return match; // leave absolute URLs untouched
      }
      const uri = webview.asWebviewUri(
        vscode.Uri.joinPath(
          this._extensionUri,
          "webview-ui",
          "webview-ui",
          "dist",
          link
        )
      );
      return `${attr}="${uri}"`;
    });

    // Inject CSP (Content Security Policy)
    html = html.replace(
      "<head>",
      `<head>
        <meta http-equiv="Content-Security-Policy"
          content="default-src 'none';
                   img-src ${webview.cspSource} https:;
                   style-src ${webview.cspSource} 'unsafe-inline';
                   script-src ${webview.cspSource};"
        >
      `
    );

    webview.html = html;
  }
}

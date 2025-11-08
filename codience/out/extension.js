"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
function activate(context) {
    const provider = new SidebarProvider(context.extensionUri);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, provider));
}
function deactivate() { }
class SidebarProvider {
    _extensionUri;
    static viewType = "sidebarView";
    constructor(_extensionUri) {
        this._extensionUri = _extensionUri;
    }
    resolveWebviewView(webviewView, context, _token) {
        const webview = webviewView.webview;
        webview.options = {
            enableScripts: true,
            localResourceRoots: [
                vscode.Uri.joinPath(this._extensionUri, "webview-ui", "webview-ui", "dist"),
            ],
        };
        const indexPath = path.join(this._extensionUri.fsPath, "webview-ui", "webview-ui", "dist", "index.html");
        let html = fs.readFileSync(indexPath, "utf-8");
        html = html.replace(/(src|href)="(.+?)"/g, (match, attr, link) => {
            if (/^https?:\/\//.test(link)) {
                return match;
            }
            const uri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionUri, "webview-ui", "webview-ui", "dist", link));
            return `${attr}="${uri}"`;
        });
        // Inject CSP (Content Security Policy)
        html = html.replace("<head>", `<head>
       <meta http-equiv="Content-Security-Policy"
      content="default-src 'none';
               img-src ${webview.cspSource} https:;
               style-src ${webview.cspSource} 'unsafe-inline';
               script-src ${webview.cspSource};
               connect-src https://codience.onrender.com;">
      `);
        webview.html = html;
    }
}
//# sourceMappingURL=extension.js.map
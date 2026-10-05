use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::path::Path;
use std::sync::Mutex;
use std::time::Duration;

use tauri::{Manager, RunEvent};
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendPort(u16);
struct BackendChild(Mutex<Option<CommandChild>>);

#[tauri::command]
fn backend_port(state: tauri::State<'_, BackendPort>) -> u16 {
    state.0
}

// --- Open folder ----------------------------------------------------------------------------------
// The page sends only a scan id and a folder id. The path comes from the backend (which answers only
// for folders holding photos in that scan) and must be an existing directory. The opener plugin is
// used from Rust only: the page has no opener permission, so it cannot open anything itself.

const LOOKUP_TIMEOUT: Duration = Duration::from_secs(2);
const MAX_REPLY_BYTES: u64 = 64 * 1024;

/// Ids are UUIDs (scan) and short hex hashes (folder); anything else is refused before any request.
fn valid_id(id: &str) -> bool {
    !id.is_empty() && id.len() <= 64 && id.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-')
}

fn folder_request(port: u16, scan_id: &str, folder_id: &str) -> String {
    format!(
        "GET /scan/folder?scan_id={scan_id}&folder_id={folder_id} HTTP/1.1\r\n\
         Host: 127.0.0.1:{port}\r\n\
         Accept: application/json\r\n\
         Connection: close\r\n\r\n"
    )
}

/// Body of a chunked HTTP/1.1 reply.
fn dechunk(mut body: &str) -> Result<String, String> {
    let mut out = String::new();
    loop {
        let (size_line, rest) = body.split_once("\r\n").ok_or("incomplete chunked reply")?;
        let size_hex = size_line.split(';').next().unwrap_or("").trim();
        let size = usize::from_str_radix(size_hex, 16).map_err(|_| "bad chunk size")?;
        if size == 0 {
            return Ok(out);
        }
        let chunk = rest.get(..size).ok_or("incomplete chunk")?;
        out.push_str(chunk);
        body = rest.get(size..).and_then(|r| r.strip_prefix("\r\n")).ok_or("bad chunk end")?;
    }
}

/// The folder path from the backend's reply to /scan/folder, or a message to show the user.
fn parse_folder_reply(raw: &[u8]) -> Result<String, String> {
    let text = std::str::from_utf8(raw).map_err(|_| "unreadable reply from the background service")?;
    let (head, body) = text.split_once("\r\n\r\n").ok_or("incomplete reply from the background service")?;
    let mut lines = head.lines();
    let status: u16 = lines
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|code| code.parse().ok())
        .ok_or("bad reply from the background service")?;
    let chunked = lines.any(|line| {
        let lower = line.to_ascii_lowercase();
        lower.starts_with("transfer-encoding:") && lower.contains("chunked")
    });
    let body = if chunked { dechunk(body)? } else { body.to_string() };
    let json: serde_json::Value =
        serde_json::from_str(body.trim()).map_err(|_| "bad reply from the background service")?;
    if status == 200 {
        json.get("path")
            .and_then(|p| p.as_str())
            .map(str::to_string)
            .ok_or_else(|| "bad reply from the background service".to_string())
    } else {
        Err(json
            .get("message")
            .and_then(|m| m.as_str())
            .unwrap_or("the folder could not be looked up")
            .to_string())
    }
}

/// Ask the backend (loopback only, 2-second timeouts) for the path of a folder in this scan.
fn lookup_folder(port: u16, scan_id: &str, folder_id: &str) -> Result<String, String> {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    let unreachable = |_| "Prism's background service isn't responding".to_string();
    let mut stream = TcpStream::connect_timeout(&addr, LOOKUP_TIMEOUT).map_err(unreachable)?;
    stream.set_read_timeout(Some(LOOKUP_TIMEOUT)).map_err(unreachable)?;
    stream.set_write_timeout(Some(LOOKUP_TIMEOUT)).map_err(unreachable)?;
    stream
        .write_all(folder_request(port, scan_id, folder_id).as_bytes())
        .map_err(unreachable)?;
    let mut raw = Vec::new();
    stream.take(MAX_REPLY_BYTES).read_to_end(&mut raw).map_err(unreachable)?;
    parse_folder_reply(&raw)
}

/// Open a folder of the current scan in Explorer. Changes nothing on disk.
#[tauri::command]
async fn open_scan_folder(app: tauri::AppHandle, scan_id: String, folder_id: String) -> Result<(), String> {
    if !valid_id(&scan_id) || !valid_id(&folder_id) {
        return Err("Invalid folder reference".into());
    }
    let port = app.state::<BackendPort>().0;
    let path = tauri::async_runtime::spawn_blocking(move || lookup_folder(port, &scan_id, &folder_id))
        .await
        .map_err(|_| "The folder lookup failed".to_string())??;
    let folder = Path::new(&path);
    if !folder.is_absolute() {
        return Err("The folder path is not valid".into());
    }
    if !folder.is_dir() {
        return Err("That folder no longer exists".into());
    }
    app.opener()
        .open_path(path, None::<&str>)
        .map_err(|e| format!("Windows could not open the folder ({e})"))
}

fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|listener| listener.local_addr())
        .map(|addr| addr.port())
        .unwrap_or(8000)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        // Used from Rust only (open_scan_folder); capabilities grant the page no opener permission
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![backend_port, open_scan_folder])
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Dev: you start the backend yourself on port 8000, as before.
            // Release: launch the bundled backend on a free port.
            let release = !cfg!(debug_assertions);
            let port = if release { free_port() } else { 8000 };
            app.manage(BackendPort(port));
            app.manage(BackendChild(Mutex::new(None)));

            if release {
                let data_dir = app.path().app_local_data_dir()?;
                std::fs::create_dir_all(&data_dir)?;
                let port_arg = port.to_string();
                let pid_arg = std::process::id().to_string();

                let (mut rx, child) = app
                    .shell()
                    .sidecar("prism-backend")?
                    .args(["--port", port_arg.as_str(), "--parent-pid", pid_arg.as_str()])
                    .env("PRISM_DATA_DIR", data_dir.to_string_lossy().to_string())
                    .spawn()?;

                // Drain the child's event channel so its pipes never fill up.
                tauri::async_runtime::spawn(async move { while rx.recv().await.is_some() {} });

                *app.state::<BackendChild>().0.lock().unwrap() = Some(child);
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(child) = handle.state::<BackendChild>().0.lock().unwrap().take() {
                let _ = child.kill();
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Instant;

    fn reply(status: &str, headers: &str, body: &str) -> Vec<u8> {
        format!("HTTP/1.1 {status}\r\n{headers}\r\n{body}").into_bytes()
    }

    #[test]
    fn parses_a_folder_path() {
        let raw = reply("200 OK", "content-type: application/json\r\ncontent-length: 51\r\n", r#"{"status":"ok","path":"C:\\Users\\Me\\Pictures\\Camera"}"#);
        assert_eq!(parse_folder_reply(&raw).unwrap(), r"C:\Users\Me\Pictures\Camera");
    }

    #[test]
    fn a_404_returns_the_backend_message() {
        let raw = reply("404 Not Found", "content-type: application/json\r\n", r#"{"status":"error","message":"Folder is not part of this scan"}"#);
        assert_eq!(parse_folder_reply(&raw).unwrap_err(), "Folder is not part of this scan");
    }

    #[test]
    fn an_error_without_a_message_gets_a_generic_one() {
        let raw = reply("500 Internal Server Error", "", "{}");
        assert_eq!(parse_folder_reply(&raw).unwrap_err(), "the folder could not be looked up");
    }

    #[test]
    fn chunked_replies_are_decoded() {
        let raw = reply("200 OK", "Transfer-Encoding: chunked\r\n", "8\r\n{\"path\":\r\nd\r\n\"D:\\\\Photos\"}\r\n0\r\n\r\n");
        assert_eq!(parse_folder_reply(&raw).unwrap(), r"D:\Photos");
    }

    #[test]
    fn malformed_replies_are_refused() {
        for raw in [&b""[..], b"HTTP/1.1 200 OK\r\n", b"garbage\r\n\r\n{}", b"HTTP/1.1 200 OK\r\n\r\nnot json", b"HTTP/1.1 200 OK\r\n\r\n{\"nopath\":1}", &[0xff, 0xfe, 0x00]] {
            assert!(parse_folder_reply(raw).is_err(), "accepted {:?}", raw);
        }
    }

    #[test]
    fn ids_are_validated() {
        assert!(valid_id("5e1adf92-db8a-40ce-a204-e44788f227b6"));
        assert!(valid_id("02f6465bda8e"));
        for bad in ["", "a b", "x&folder_id=y", "..\\..", "id\r\nHost: evil", &"a".repeat(65)] {
            assert!(!valid_id(bad), "accepted {bad:?}");
        }
    }

    #[test]
    fn request_has_host_and_connection_close() {
        let r = folder_request(51234, "scan-1", "abc123");
        assert!(r.starts_with("GET /scan/folder?scan_id=scan-1&folder_id=abc123 HTTP/1.1\r\n"));
        assert!(r.contains("\r\nHost: 127.0.0.1:51234\r\n"));
        assert!(r.contains("\r\nConnection: close\r\n"));
        assert!(r.ends_with("\r\n\r\n"));
    }

    #[test]
    fn lookup_talks_to_the_loopback_backend() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let server = std::thread::spawn(move || {
            let (mut sock, _) = listener.accept().unwrap();
            let mut buf = [0u8; 1024];
            let n = sock.read(&mut buf).unwrap();
            let request = String::from_utf8_lossy(&buf[..n]).to_string();
            sock.write_all(b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\nconnection: close\r\n\r\n{\"path\":\"C:\\\\x\"}").unwrap();
            request
        });
        assert_eq!(lookup_folder(port, "s1", "f1").unwrap(), r"C:\x");
        let request = server.join().unwrap();
        assert!(request.contains(&format!("Host: 127.0.0.1:{port}")));
    }

    #[test]
    fn a_silent_backend_times_out_after_about_two_seconds() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let _server = std::thread::spawn(move || {
            let (_sock, _) = listener.accept().unwrap();
            std::thread::sleep(Duration::from_secs(5)); // accepts, never answers
        });
        let start = Instant::now();
        assert!(lookup_folder(port, "s1", "f1").is_err());
        let took = start.elapsed();
        assert!(took >= Duration::from_millis(1900) && took < Duration::from_secs(4), "took {took:?}");
    }
}
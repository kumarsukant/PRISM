use std::net::TcpListener;
use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendPort(u16);
struct BackendChild(Mutex<Option<CommandChild>>);

#[tauri::command]
fn backend_port(state: tauri::State<'_, BackendPort>) -> u16 {
    state.0
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
        .invoke_handler(tauri::generate_handler![backend_port])
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
// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn get_settings() -> Result<String, String> {
    // Find the home directory
    let home_dir = dirs::home_dir().ok_or_else(|| "Could not find home directory".to_string())?;

    // Construct the path to settings.json
    let mut settings_path = home_dir;
    settings_path.push("rubberduck");
    settings_path.push("settings.json");

    // Read the file if it exists, otherwise return an empty JSON object
    if settings_path.exists() {
        std::fs::read_to_string(&settings_path)
            .map_err(|e| format!("Failed to read settings.json: {}", e))
    } else {
        Ok("{}".to_string())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![greet, get_settings])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_settings() {
        let res = get_settings();
        println!("Settings result: {:?}", res);
    }
}

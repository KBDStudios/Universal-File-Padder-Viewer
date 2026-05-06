<img width="1363" height="674" alt="Demonstration Universal-File-Padder-Viewer" src="https://github.com/user-attachments/assets/e57a903c-110a-4819-bb7b-2109ad2a5edf" />

# Universal File Padder & Viewer

A specialized GUI utility developed by **KBDStudios** strictly designed to append exact amounts of binary null padding (`\x00`) to the end of any file. 

**This tool does not compress, re-encode, or alter your original file data.** It exclusively pads files. This is designed for binary modification workflows where internal pointers require compiled file blocks to meet exact byte-size requirements. By mathematically inflating a smaller modified file to match the original file's size, you prevent internal structure shifts and subsequent engine crashes.

## 💻 **System Requirements & Architecture:**

**Pre-compiled Release (.exe):**
The standalone release build is compiled specifically for **Client Windows** environments (x64/x86 architecture).

**Source Code (Python):**
If you want to use this on **macOS**, **Linux**, or other operating systems, you can simply download the source code and run the Python scripts natively using your own Python environment.

## ✨ Features

* **Strict End-of-File Padding:** Safely injects null bytes (`\x00`) at the end of any file without touching the original data structure.
* **Target Size Matching:** Right-click a loaded file and select an original game asset to automatically calculate and append the exact padding needed to perfectly match their sizes.
* **Batch Processing:** Select multiple files and apply a uniform padding amount to all of them at once. 
* **Flexible Padding Units:** Input and view padding amounts natively across Bytes, KB, MB, and GB (supports up to a 5GB absolute padding limit per file).
* **Live Image Previews:** If you are padding supported UI textures (PNG, JPG, BMP, TIFF, TGA, WEBP, AVIF, GIF), you can view them directly in the scrollable gallery.
* **Threaded Animation Playback:** Play animated formats (GIF, WEBP) directly in the preview gallery without freezing the UI.
* **Full-Resolution Viewer:** Double-click any loaded image to open an advanced viewer with zoom controls and a hover magnifier.

## 🚀 Installation & Usage

### Option 1: Standalone Executable (Easiest)
For users who just want to run the program without installing Python:
1. Navigate to the **Releases** tab on the right side of this page.
2. Download the latest `Universal_File_Padder.exe`.
3. Double-click to run! 

🛡️ **Note on Windows "Unknown Publisher" Warning:**
Because this is an independently developed freeware tool, the executable is not signed with a commercial Microsoft certificate. When you first run the program, Windows SmartScreen might show a blue "Windows protected your PC" popup. Don't worry! To bypass this, simply click **More info**, and then click **Run anyway**.

### Option 2: Running from Source
For developers or users running the raw Python script:
1. Ensure you have **Python 3.x** installed on your system.
2. Clone or download this repository.
3. Install the required image processing library by opening your command prompt and typing:

       pip install pillow

4. Run the `UniversalFilePadderViewer.pyw` script.

## ⚠️ **File Exports & Windows Security:**
Windows "Tamper Protection" (often tied to **Real-time protection** in Client Windows 7/10/11) or third-party antivirus software may sometimes block the tool from exporting files.

If your exports are failing, simply add the tool's folder to your antivirus exclusions:
1. Open **Windows Security** > **Virus & threat protection**.
2. Under *Virus & threat protection settings*, click **Manage settings**.
3. Scroll down to *Exclusions* and click **Add or remove exclusions**.
4. Click **Add an exclusion** > **Folder**, and select the folder where this tool is located.

*(Note: While you can temporarily disable Tamper/Real-time protection to force an export, adding a folder exclusion is safer and only needs to be done once.)*

## 📄 License
This software is provided under a custom Proprietary Freeware License. It is strictly for personal, non-commercial use. Modification or creation of derivative works is prohibited. Please see the LICENSE.txt file for complete details.

---
**Author:** KabirDigitalStudios (KBDStudios)

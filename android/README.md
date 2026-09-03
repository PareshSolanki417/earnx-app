# EarnX Android APK Project (Secure WebView Wrapper)

This project wraps the hosted EarnX web application into a secure, release-ready Android APK.

## Key Security & Architectural Highlights
1. **Isolated Backend**: The APK contains no API secrets, database passwords, or ad network tokens.
2. **HTTPS Only**: `android:usesCleartextTraffic="false"` prevents insecure HTTP connections.
3. **Safe Navigation Handler**: External intents (Telegram `tg://` & `t.me`, WhatsApp, mailto, tel) safely trigger native Android apps while application routes remain in the secure WebView.
4. **Offline Resiliency**: Displays an interactive offline screen with a retry button if network connectivity is lost.
5. **Back Navigation**: Hardware back button intelligently steps backward through the web browsing history.

---

## How to Build the APK

### Prerequisites
- Android Studio (Hedgehog 2023.1+ or newer)
- Android SDK (API 34)
- JDK 17+

### Step-by-Step Instructions
1. Open **Android Studio**.
2. Select **File -> Open...** and browse to the `android/` directory inside this repository.
3. Allow Gradle to synchronize dependencies.
4. Set your production web app URL:
   - Open `android/app/src/main/res/values/strings.xml`
   - Update `<string name="webapp_url">https://YOUR-RENDER-DOMAIN/</string>` with your live Render URL.
5. To test locally on an emulator:
   - Run the FastAPI backend locally on port 8000.
   - For Android Emulator, use `http://10.0.2.2:8000/` as the URL (ensure cleartext traffic is temporarily permitted for local dev).
6. To generate a signed Release APK:
   - Go to **Build -> Generate Signed Bundle / APK...**
   - Select **APK**
   - Create or select your keystore
   - Select **release** build variant and click **Finish**.
   - Your production APK will be output to `android/app/release/app-release.apk`.

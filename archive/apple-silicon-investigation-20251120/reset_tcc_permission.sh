#!/bin/bash
# Script to help reset TCC microphone permissions for testing

echo "🔓 TCC Microphone Permission Reset Helper"
echo "=========================================="
echo ""

# Get the bundle ID of Terminal or the running application
CURRENT_APP=$(osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true')

echo "Current application: $CURRENT_APP"
echo ""

echo "This script will help you reset microphone permissions."
echo ""
echo "⚠️  IMPORTANT: You need to do this MANUALLY in System Settings"
echo ""
echo "Steps to reset/add microphone permission:"
echo ""
echo "1. Open System Settings:"
echo "   - Click the Apple menu () → System Settings"
echo ""
echo "2. Navigate to Privacy & Security:"
echo "   - In the left sidebar, click 'Privacy & Security'"
echo "   - Scroll down and click 'Microphone'"
echo ""
echo "3. You should see a list of apps. Look for:"
if [[ "$CURRENT_APP" == "Terminal" ]] || [[ "$CURRENT_APP" == "iTerm2" ]]; then
    echo "   • Terminal (or iTerm2)"
    echo "   • Python"
    echo "   • python3.12"
elif [[ "$CURRENT_APP" == "Code" ]] || [[ "$CURRENT_APP" == "Visual Studio Code" ]]; then
    echo "   • Code"
    echo "   • Visual Studio Code"
else
    echo "   • $CURRENT_APP"
    echo "   • Python"
    echo "   • python3.12"
fi
echo ""
echo "4. If the app is in the list:"
echo "   • If unchecked: Check the box to enable ✓"
echo "   • If checked but not working: Uncheck, then check again"
echo ""
echo "5. If the app is NOT in the list:"
echo "   This means the app hasn't requested permission yet."
echo "   The permission dialog should appear when you run the test."
echo ""
echo "6. Alternative method - Reset TCC database (requires admin password):"
echo "   This will reset ALL microphone permissions:"
echo ""
echo "   tccutil reset Microphone"
echo ""
echo "   After running this command, the permission dialog will appear"
echo "   the next time any app requests microphone access."
echo ""
echo "=========================================="
echo ""
read -p "Press Enter to open System Settings to Privacy & Security → Microphone..."
echo ""

# Open System Settings to microphone page
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"

echo "✅ System Settings opened"
echo ""
echo "After granting permission, run your test again:"
echo "  python3.12 examples/macos_pyobjc_capture_test.py --pid <PID> --duration 5"
echo ""
echo "Or use the quick test script:"
echo "  ./quick_test.sh"
echo ""

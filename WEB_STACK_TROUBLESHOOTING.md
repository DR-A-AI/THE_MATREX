# 🚀 Web Stack Troubleshooting Guide

**Problem**: "This site can't be reached" when accessing http://127.0.0.1:5173

---

## 🔍 Quick Diagnosis

### Run the diagnostic:
```bash
DIAGNOSTIC.bat    # Windows
./DIAGNOSTIC.sh   # Linux/Mac
```

---

## ✅ Solutions (Try in Order)

### Solution 1: Kill Conflicting Processes
```powershell
# Kill any Node.js on port 5173
taskkill /F /IM node.exe

# Verify port is free
netstat -ano | findstr ":5173"
# Should return: (empty)
```

### Solution 2: Reinstall NPM Dependencies
```bash
cd dashboard
npm install
npm run dev
```

If `npm: command not found`, install Node.js from https://nodejs.org

### Solution 3: Check Firewall
Windows may block ports 5173 and 8000:

1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Find and allow "Node.js" or manual port exceptions
4. Add ports: 5173 (Vite), 8000 (FastAPI)

### Solution 4: Manual Testing

**Terminal 1** - Dashboard:
```bash
cd J:\THE_MATRIX\dashboard
npm run dev
# Should output: 
# VITE v8.0.12  ready in 234 ms
# ➜  Local:   http://127.0.0.1:5173/
```

**Terminal 2** - UI Bridge:
```bash
cd J:\THE_MATRIX
python services/ui_bridge.py
# Should output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Terminal 3** - Core Engine:
```bash
cd J:\THE_MATRIX
python matrix_main.py
# Should output:
# ✓ All core systems online
```

**Browser**:
- Dashboard: http://127.0.0.1:5173
- API Docs: http://127.0.0.1:8000/docs
- WebSocket: ws://127.0.0.1:8000/ws

---

## 🛠️ Improved IGNITE_MATRIX.bat

Updated with:
- ✅ Auto-kill port 5173 conflicts
- ✅ Proper window titles for each service
- ✅ Longer startup wait (5 seconds for Vite)
- ✅ Clear endpoint URLs displayed
- ✅ Better error handling

**To use**:
```bash
# From command line or double-click
IGNITE_MATRIX.bat
```

---

## 📊 Port Summary

| Service | Port | URL | Status |
|---------|------|-----|--------|
| **Vite Dashboard** | 5173 | http://127.0.0.1:5173 | React UI |
| **FastAPI UI Bridge** | 8000 | http://127.0.0.1:8000 | WebSocket + REST |
| **ZMQ Neural Bus** | 5555 | tcp://127.0.0.1:5555 | Internal IPC |

---

## 🔧 Vite Config

Updated `dashboard/vite.config.js` with:
- Explicit host/port binding
- WebSocket proxy to FastAPI
- API proxy to Backend
- Non-strict port mode (fallback if 5173 unavailable)

---

## 🆘 If Still Failing

1. **Check Event Viewer** (Windows)
   - Search "Event Viewer"
   - Look for application errors

2. **Check antivirus**
   - Some antivirus blocks Node.js
   - Try disabling temporarily to test

3. **Verify Python** (3.10+)
   ```bash
   python --version
   ```

4. **Verify Node.js** (14+ recommended)
   ```bash
   npm --version
   node --version
   ```

5. **Try different port**
   - Edit vite.config.js: change `port: 5173` to `port: 3000`
   - Edit ui_bridge.py: change `port=8000` to `port=9000`

6. **Check logs**
   - Each window shows logs
   - Copy errors and search online
   - Or test manually (Solution 4 above)

---

## ✨ Expected Output

When everything works:

**Vite Window**:
```
  VITE v8.0.12  ready in 234 ms

  ➜  Local:   http://127.0.0.1:5173/
  ➜  press h to show help
```

**UI Bridge Window**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**Core Engine Window**:
```
2026-06-09 14:03:31,580 - [INFO] - Matrix.Boot: =======================================
2026-06-09 14:03:31,580 - [INFO] - Matrix.Boot: BOOTING THE SOVEREIGN MATRIX ENGINE
2026-06-09 14:03:31,580 - [INFO] - Matrix.Boot: =======================================
```

Then browse to: **http://127.0.0.1:5173** 🎉

---

## 📚 Files Modified

1. **IGNITE_MATRIX.bat** - Improved startup script
2. **dashboard/vite.config.js** - Added server config
3. **DIAGNOSTIC.bat** - New Windows diagnostic tool

---

**Last Updated**: 2026-06-09

![GitHub release](https://img.shields.io/github/v/release/listellionline/yt-cut-merge-gui)
![GitHub downloads](https://img.shields.io/github/downloads/listellionline/yt-cut-merge-gui/total)
![License](https://img.shields.io/github/license/listellionline/yt-cut-merge-gui)
# 🎬 YT Cut Merge GUI

> Scarica, taglia e unisce clip video da YouTube o file locali — con interfaccia grafica semplice e potente.

---

## 🚀 Funzionalità

* 🎥 Download video da URL (YouTube, ecc.)
* ✂️ Taglio clip multiple (file o CSV)
* 🔗 Merge automatico in un unico video
* 🎬 Transizioni con fade tra clip
* ⚙️ Ricodifica opzionale
* 📂 Gestione file direttamente dalla GUI
* 📊 Barra di progresso dettagliata
* 🧠 Rilevamento automatico file già scaricati

---

## 🖥️ Piattaforme supportate

* ✅ Debian / Linux
* ✅ Windows (installer incluso)

---

## 📦 Installazione

### 🐧 Linux (Debian)

```bash
./packaging/debian/install.sh
```

Avvio:

```bash
gtk-launch yt-cut-merge
```

---

### 🪟 Windows

Scarica l’installer da:
👉 **Releases**

Installa e avvia dal menu Start.

---

## 🎯 Utilizzo

### 1. Seleziona sorgente

* URL → incolla link YouTube
* Locale → scegli file video

### 2. Seleziona clip

* File `.txt`
* Oppure CSV:

```text
00:01:00-00:02:00,00:03:00-00:05:00
```

### 3. Opzioni

* Fade tra clip 🎬
* Ricodifica 🔄

### 4. Avvia

👉 Click su **Start**

---

## 📂 Gestione video

* Doppio click → apre video
* Click destro:

  * Apri
  * Rinomina
  * Elimina
  * Copia percorso

---

## ⚙️ Dipendenze

* ffmpeg
* yt-dlp

(automatiche su Windows)

---

## 🧑‍💻 Autore

**Antonio Fiumara**

---

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT.

---

## ⭐ Supporto

Se ti piace il progetto:
👉 lascia una ⭐ su GitHub!


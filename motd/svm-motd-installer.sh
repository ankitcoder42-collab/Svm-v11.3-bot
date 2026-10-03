#!/bin/bash
# ==========================================
# SVM v11.2 AI System Premium MOTD Installer
# FULL CLEAN + ONLY CUSTOM MOTD
# (runs inside each new VPS; shipped locally — nothing is downloaded)
# ==========================================

set -e

echo "🔧 Installing SVM v11.2 AI System Premium MOTD..."

# ================================
# REMOVE ALL OLD MOTD SYSTEM
# ================================
echo "🧹 Removing old MOTD completely..."

chmod -x /etc/update-motd.d/* 2>/dev/null || true

rm -f /etc/motd
rm -f /var/run/motd
rm -f /run/motd.dynamic

# Disable motd-news
if [ -f /etc/default/motd-news ]; then
    sed -i 's/ENABLED=1/ENABLED=0/g' /etc/default/motd-news
fi

# ================================
# FORCE ONLY OUR MOTD (PAM FIX)
# ================================
echo "⚙ Configuring PAM..."

mkdir -p /etc/update-motd.d

cp /etc/pam.d/sshd /etc/pam.d/sshd.bak 2>/dev/null || true
cp /etc/pam.d/login /etc/pam.d/login.bak 2>/dev/null || true

sed -i '/pam_motd.so/d' /etc/pam.d/sshd 2>/dev/null || true
sed -i '/pam_motd.so/d' /etc/pam.d/login 2>/dev/null || true

# Prevent duplicate entries
sed -i '\|00-svm-ai-system|d' /etc/pam.d/sshd 2>/dev/null || true
sed -i '\|00-svm-ai-system|d' /etc/pam.d/login 2>/dev/null || true

[ -f /etc/pam.d/sshd ] && echo "session optional pam_exec.so stdout /etc/update-motd.d/00-svm-ai-system" >> /etc/pam.d/sshd
[ -f /etc/pam.d/login ] && echo "session optional pam_exec.so stdout /etc/update-motd.d/00-svm-ai-system" >> /etc/pam.d/login

# ================================
# CREATE SVM v11.2 AI MOTD
# ================================
echo "✨ Creating SVM v11.2 AI System MOTD..."

cat << 'EOF' > /etc/update-motd.d/00-svm-ai-system
#!/bin/bash

# ===== Colors =====
GREEN="\e[38;5;82m"
CYAN="\e[38;5;51m"
BLUE="\e[38;5;39m"
MAGENTA="\e[38;5;213m"
YELLOW="\e[38;5;220m"
RED="\e[38;5;196m"
GRAY="\e[38;5;245m"
WHITE="\e[97m"
RESET="\e[0m"

# ===== System Information =====

HOSTNAME=$(hostname)

OS=$(grep PRETTY_NAME /etc/os-release 2>/dev/null |
     cut -d= -f2 | tr -d '"')

KERNEL=$(uname -r)

UPTIME=$(uptime -p 2>/dev/null | sed 's/up //' || echo "Unknown")

# CPU
CPU=$(top -bn1 2>/dev/null |
      grep "Cpu(s)" |
      awk '{print 100 - $8"%"}' ||
      echo "N/A")

# Memory
MEM_TOTAL=$(free -m | awk '/Mem:/ {print $2}')
MEM_USED=$(free -m | awk '/Mem:/ {print $3}')

if [ -n "$MEM_TOTAL" ] && [ "$MEM_TOTAL" -gt 0 ]; then
    MEM_PERC=$((MEM_USED * 100 / MEM_TOTAL))
else
    MEM_PERC=0
fi

# Disk
DISK=$(df -h / 2>/dev/null |
       awk 'NR==2 {print $3 " / " $2 " (" $5 ")"}' ||
       echo "N/A")

# IP
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
IP=${IP:-N/A}

# Users
USERS=$(who 2>/dev/null | wc -l)

# Processes
PROCS=$(ps -e --no-headers 2>/dev/null | wc -l)

echo ""

# ==========================================
# SVM v11.2 AI SYSTEM LOGO
# ==========================================

echo -e "${MAGENTA}"

cat << "LOGO"

 ███████╗██╗   ██╗███╗   ███╗
 ██╔════╝██║   ██║████╗ ████║
 ███████╗██║   ██║██╔████╔██║
 ╚════██║╚██╗ ██╔╝██║╚██╔╝██║
 ███████║ ╚████╔╝ ██║ ╚═╝ ██║
 ╚══════╝  ╚═══╝  ╚═╝     ╚═╝

 ██████╗ ██╗ ██╗
 ██╔══██╗██║███║
 ██║  ██║██║╚██║
 ██║  ██║██║ ██║
 ██████╔╝██║ ██║
 ╚═════╝ ╚═╝ ╚═╝

        v11.2 AI SYSTEM

LOGO

echo -e "${RESET}"

# ==========================================
# HEADER
# ==========================================

echo -e "${GREEN}🤖 Welcome to SVM v11.2 AI System${RESET}"
echo -e "${BLUE}Advanced AI • High Performance • Secure Infrastructure${RESET}"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# ==========================================
# SYSTEM STATUS
# ==========================================

printf "${CYAN}%-18s${RESET} %s\n" "Hostname:" "$HOSTNAME"
printf "${CYAN}%-18s${RESET} %s\n" "OS:" "$OS"
printf "${CYAN}%-18s${RESET} %s\n" "Kernel:" "$KERNEL"
printf "${CYAN}%-18s${RESET} %s\n" "Uptime:" "$UPTIME"
printf "${CYAN}%-18s${RESET} %s\n" "CPU Usage:" "$CPU"

printf "${CYAN}%-18s${RESET} %sMB / %sMB (${YELLOW}%s%%${RESET})\n" \
"Memory:" "$MEM_USED" "$MEM_TOTAL" "$MEM_PERC"

printf "${CYAN}%-18s${RESET} %s\n" "Disk:" "$DISK"
printf "${CYAN}%-18s${RESET} %s\n" "Processes:" "$PROCS"
printf "${CYAN}%-18s${RESET} %s\n" "Users:" "$USERS"
printf "${CYAN}%-18s${RESET} %s\n" "IP:" "$IP"

echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# ==========================================
# SVM SERVICES
# ==========================================

echo -e "${GREEN}⚡ SVM System:${RESET}  ${WHITE}v11.2 AI${RESET}"
echo -e "${GREEN}🧠 AI Engine:${RESET}    ${WHITE}Online${RESET}"
echo -e "${GREEN}🔐 Security:${RESET}     ${WHITE}Active${RESET}"
echo -e "${GREEN}🖥️  WebSSH:${RESET}       ${WHITE}Available${RESET}"

echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# ==========================================
# SUPPORT
# ==========================================

echo -e "${GREEN}Support:${RESET}  SVM Support"
echo -e "${GREEN}Discord:${RESET}  SVM Discord"
echo -e "${GREEN}WebSSH:${RESET}   WebSSH"

echo -e "${MAGENTA}SVM v11.2 AI System — Advanced Server Infrastructure 🤖${RESET}"

echo ""

EOF

chmod +x /etc/update-motd.d/00-svm-ai-system

# ================================
# RESTART SSH
# ================================

systemctl restart ssh 2>/dev/null || \
systemctl restart sshd 2>/dev/null || true

echo ""
echo "✅ SVM v11.2 AI System MOTD Installed"
echo "🚫 All default MOTD disabled"
echo "🤖 Only SVM v11.2 AI MOTD will show"
echo "➡ Reconnect SSH to see changes"

# 🏦 Enterprise Bank System - Infrastructure & Deployment

### 🛰️ Overview
Этот проект представляет собой микросервисную архитектуру банковской системы, упакованную в Docker-контейнеры и подготовленную к автоматизированному развертыванию через Packer. 
*Фокус проекта: Безопасность, масштабируемость и Infrastructure as Code (IaC).*

### 🛠️ Tech Stack
* **Core:** Python (Backend Logic)
* **Environment:** Docker & Docker-Compose (Containerization)
* **Automation:** HashiCorp Packer (Immutable Infrastructure)
* **OS Baseline:** Ubuntu 22.04 LTS (Hardened)

### 🛡️ Infrastructure Features
1. **Immutable Images:** Использование Packer для создания "золотых образов", что исключает ошибки ручной настройки сервера.
2. **Container Security:** Изоляция банковских модулей друг от друга.
3. **Automated CI/CD Ready:** Конфиги подготовлены для интеграции в любой современный пайплайн.

### 🚀 How to deploy
```bash
# 1. Сборка образа через Packer
packer build base_image.pkr.hcl

# 2. Запуск системы
docker-compose up -d
```

### 📈 Roadmap
- [ ] Интеграция с Terraform для облачного деплоя.
- [ ] Настройка мониторинга через Prometheus/Grafana.
- [ ] Внедрение Vault для хранения секретов (API ключей).
- [ ] 
- [ ] если хотите следить за развитием других проектов: https://t.me/Ierihonlog

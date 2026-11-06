<div align="center">

**Gestor profesional de conexiones SSH para Ubuntu — GUI + CLI con un motor compartido.**

`sss prod` · `sss prod nginx` · `sss prod --exec "uptime"`

[English](README.md) · [فارسی](README.fa.md) · [العربية](README.ar.md) · [简体中文](README.zh.md) · [Русский](README.ru.md) · **Español** · [Français](README.fr.md)

</div>

SSH Desk es un producto real e instalable (no un prototipo) para gestionar todos tus servidores SSH: las contraseñas se guardan **solo** en GNOME Keyring (Secret Service), el motor SSH es el **OpenSSH del sistema** y el terminal integrado es una **PTY real** (vim/nano, colores, Ctrl+C, cambio de tamaño — todo funciona de verdad).

- 🖥️ **GUI de escritorio** (PySide6): temas oscuro/claro, persa/inglés (RTL completo), pestañas de terminal reales, gestor de archivos SFTP, túneles, claves, historial
- ⌨️ **CLI** (Typer): funciona **sin** la GUI; nombre del comando configurable (`sss`, `cnc`, `sshgo`, …); autocompletado bash/zsh con alias de servidores
- 🔐 **Seguridad primero**: verificación estricta de host keys con diálogo de huella; los secretos nunca llegan a la base de datos/logs/argv; sin `sshpass` y sin `StrictHostKeyChecking=no`
- 🌐 **Resistente a cortes de red**: cadena de espejos de PyPI (oficial → ArvanCloud (Irán) → TUNA → Aliyun → Tencent) e instalación totalmente sin conexión con `install.sh --offline`

📄 **[Guía de usuario completa (PDF, en persa)](docs/SSH-Desk-User-Guide-fa.pdf)** — 14 páginas ilustradas: instalación sin conexión, referencia CLI completa, terminal, SFTP, túneles y modelo de seguridad.

---

## Inicio rápido

```bash
git clone https://github.com/hmplus28/SSH-Desk.git
cd SSH-Desk
bash scripts/install.sh
```

Después:

```bash
ssh-desk          # interfaz gráfica
sss add           # añadir el primer servidor
sss prod          # conectar (shell interactivo en tu terminal)
```

Paquete DEB e instalación manual: [docs/INSTALLATION.md](docs/INSTALLATION.md).
Redes inestables o sin conexión: `bash scripts/download_wheels.sh --mirror-name ir` y luego `bash scripts/install.sh --offline`.

## La CLI en 30 segundos

```bash
sss                      # resumen + pistas
sss list                 # tabla de servidores
sss add                  # asistente interactivo (o --alias/--host/...)
sss info prod            # detalles completos
sss test prod            # prueba de conectividad
sss prod                 # shell interactivo en la ruta predeterminada
sss prod nginx           # conectar a una ruta guardada
sss prod /etc/nginx      # conectar a una ruta absoluta
sss prod --exec "uptime" # ejecutar un comando (no guarda nada)
sss prod --user ubuntu --port 2222   # anulación solo para esta ejecución
sss history              # historial de conexiones
sss current              # sesiones activas + túneles en ejecución
sss tunnel db            # iniciar un túnel con nombre (sobrevive al terminal)
sss config cli-name cnc  # renombrar el comando a nivel del sistema
sss --help               # referencia completa
```

## Características

| Área | Lo que funciona |
| --- | --- |
| Servidores | CRUD, alias únicos, grupos, etiquetas, favoritos, duplicar, buscar/ordenar/filtrar |
| Autenticación | Contraseña (Keyring), clave privada (+frase en Keyring), agente SSH, interactiva |
| Rutas | Ruta predeterminada + rutas guardadas con nombre (`sss prod nginx`), entrecomillado seguro |
| Terminal | PTY real (OpenSSH), múltiples pestañas, colores, vim/nano, redimensionar, copiar/pegar |
| Archivos | Gestor SFTP de dos paneles: subir/descargar/mkdir/renombrar/chmod/editar/borrar + transferencia servidor↔servidor |
| Claves | Generación Ed25519/RSA/ECDSA en formato OpenSSH, importar, huella, exportar clave pública, guía de `ssh-copy-id` |
| Túneles | Local / Remoto / SOCKS dinámico, iniciar/detener, demonio independiente, seguimiento de estado |
| Jump hosts | `ProxyCommand` vía `ssh -W` a través de cualquier servidor registrado (cadenas anidadas) |
| Comandos | Comandos guardados por servidor o globales, confirmación para los peligrosos |
| Historial | Conexión/desconexión, duración, estado, errores (sin contenido del terminal ni contraseñas) |
| Importar/Exportar | Importación de `~/.ssh/config` con vista previa y deduplicación, copia/restauración TOML (secretos opcionales) |

## Modelo de seguridad (versión corta)

1. Las contraseñas/frases viven **solo** en el Secret Service (GNOME Keyring); la BD guarda una referencia sin secretos.
2. OpenSSH recibe los secretos mediante un **helper askpass** reforzado — nunca por argv, ni por entorno, ni con sshpass.
3. La verificación de host keys es obligatoria (`StrictHostKeyChecking=yes`): desconocido → diálogo de huella; cambiado → aviso estricto.
4. Archivos de BD/configuración con permisos `0600`/`0700`; logs depurados; sin demonios root.

Detalles completos: [docs/SECURITY.md](docs/SECURITY.md).

## Desarrollo

```bash
pip install -e .[dev]
pytest          # 54 tests
ruff check .    # clean
```

Arquitectura e internals: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ·
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) · [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

## Requisitos

- Ubuntu 22.04 / 24.04+ (o cualquier distro basada en Debian)
- Python 3.10+ (se recomienda 3.12), `openssh-client`
- GNOME Keyring para guardar contraseñas (`sudo apt install gnome-keyring`)

## Licencia

MIT — véase [LICENSE](LICENSE).

# Bootstrap нативной лаборатории 1С

Проверено 25 августа 2026 года для чистого Debian 13 (`trixie`, `x86_64`) контейнера. Рецепт восстанавливает именно стенд этапа 0; это не универсальный установщик 1С.

## Предпосылки

- Основная папка Hermes Project и Git-корень: `/workspace/1c-agent-harness`.
- Команды агента исполняются локально внутри активного WebUI-контейнера от uid 1024 (`hermeswebui`); `sudo` и Docker socket внутри контейнера отсутствуют.
- На host доступен одноразовый `docker exec -u root <container-id> ...`.
- В контейнере есть Bash, Git, CA certificates, `apt-get`, `apt-cache`, `dpkg-deb`, `curl`, Python 3, Debian archive keyring, `ldd` (`libc-bin`), а также стандартные `coreutils` и `findutils`.
- Во время root-шагов не должны работать конкурирующие процессы от workspace uid.

## 0. Создать Git Workspace

В новой пустой основной папке Hermes Project:

```bash
set -euo pipefail
cd /workspace/1c-agent-harness
test -z "$(find . -mindepth 1 -maxdepth 1 -print -quit)"
git clone https://github.com/Kwentin3/1c-agent-harness.git .
test "$(git rev-parse --show-toplevel)" = "$PWD"
mkdir -p .local/dist .local/platform .local/tools .local/cache .local/runs
git check-ignore -q .local/
```

## 1. Получить закрытый installer и открытый fixture

Учебный installer выдаётся после анкеты, принятия лицензии и получения временной ссылки по email:

<https://online.1c.ru/catalog/programs/program/36179915/>

Сохраните его как:

```text
.local/dist/setup-training-8.5.1.1150-x86_64.run
```

Проверьте до любого запуска:

```bash
set -euo pipefail
cd /workspace/1c-agent-harness
printf '%s  %s\n' '396b7065b9efb6272093f1bda5eab647081a13d9ccbb4c5cfb0e711346d5af28' '.local/dist/setup-training-8.5.1.1150-x86_64.run' | sha256sum -c -
```

Скачайте официальный Jet fixture и проверьте digest:

```bash
set -euo pipefail
cd /workspace/1c-agent-harness
mkdir -p .local/dist .local/platform .local/tools
DEST=.local/dist/Jet-1.0.3.1-tr.cf
test ! -e "$DEST"
test ! -L "$DEST"
TMP=$(mktemp .local/dist/.Jet-1.0.3.1-tr.cf.XXXXXX)
trap 'rm -f "$TMP"' EXIT
curl -fL --retry 3 -o "$TMP" 'https://github.com/1Ci-Company/Jet/releases/download/v1.0.3.1-tr/1.0.3.1.cf'
printf '%s  %s\n' '5694f9e4bdf9a0857185118ba816d562d8ee8de2b8da3f60792397a399ca128a' "$TMP" | sha256sum -c -
chmod 0444 "$TMP"
ln "$TMP" "$DEST"
rm -f "$TMP"
trap - EXIT
```

## 2. Установить учебную платформу одноразовым root-шагом

Ниже `<container-id>` заменяется фактическим ID. Installer сначала копируется как данные в root-owned staging и там повторно проверяется. Команда рассчитана на доверенный single-user контейнер без конкурирующих процессов.

```bash
docker exec -u root <container-id> bash -c 'set -euo pipefail; SRC=/workspace/1c-agent-harness/.local/dist/setup-training-8.5.1.1150-x86_64.run; test -f "$SRC"; test ! -L "$SRC"; test ! -e /opt/1cv8t; test ! -L /opt/1cv8t; STAGE=$(mktemp -d /root/1c-stage.XXXXXX); install -m 0700 "$SRC" "$STAGE/setup.run"; printf "%s  %s\n" 396b7065b9efb6272093f1bda5eab647081a13d9ccbb4c5cfb0e711346d5af28 "$STAGE/setup.run" | sha256sum -c -; "$STAGE/setup.run" --mode unattended --unattendedmodeui none --installer-language en; rm -f "$STAGE/setup.run"; rmdir "$STAGE"; test -x /opt/1cv8t/x86_64/8.5.1.1150/1cv8t; echo TRAINING_INSTALLED'
```

Переместите единственную установленную копию в workspace. Команда отказывается перезаписывать destination и проверяет, что ancestors не являются symlink:

```bash
docker exec -u root <container-id> bash -c 'set -euo pipefail; ROOT=/workspace/1c-agent-harness; test "$(readlink -f "$ROOT")" = "$ROOT"; test "$(readlink -f "$ROOT/.local")" = "$ROOT/.local"; test "$(readlink -f "$ROOT/.local/platform")" = "$ROOT/.local/platform"; test "$(stat -c %u "$ROOT/.local/platform")" = 1024; DST="$ROOT/.local/platform/1cv8t"; test ! -e "$DST"; test ! -L "$DST"; mv /opt/1cv8t "$DST"; chown -R 1024:1024 "$DST"; test -x "$DST/x86_64/8.5.1.1150/1cv8t"; echo TRAINING_MOVED'
```

## 3. Подготовить локальный GUI/Xvfb runtime без системной установки

В 1С 8.5 используется GTK3 и WebKit2GTK 4.0. Последнего нет в trixie, поэтому проверенный runtime сочетает базовый GUI/Xvfb слой trixie с закреплённым ABI-набором WebKit/transitive из bookworm.

Создайте user-space APT root:

```bash
set -euo pipefail
cd /workspace/1c-agent-harness
APTROOT="$PWD/.local/tools/aptroot"
mkdir -p "$APTROOT"/{etc/apt,state/lists/partial,cache/archives/partial}
printf '%s\n' \
  'deb [check-valid-until=no signed-by=/usr/share/keyrings/debian-archive-keyring.pgp] https://snapshot.debian.org/archive/debian/20260825T000000Z trixie main' \
  'deb [check-valid-until=no signed-by=/usr/share/keyrings/debian-archive-keyring.pgp] https://snapshot.debian.org/archive/debian-security/20260825T000000Z trixie-security main' \
  'deb [check-valid-until=no signed-by=/usr/share/keyrings/debian-archive-keyring.pgp] https://snapshot.debian.org/archive/debian/20260825T000000Z bookworm main' \
  'deb [check-valid-until=no signed-by=/usr/share/keyrings/debian-archive-keyring.pgp] https://snapshot.debian.org/archive/debian-security/20260825T000000Z bookworm-security main' \
  > "$APTROOT/etc/apt/sources.list"
APT_OPTS=(-o "Dir::Etc::sourcelist=$APTROOT/etc/apt/sources.list" -o Dir::Etc::sourceparts=- -o "Dir::State::lists=$APTROOT/state/lists" -o "Dir::Cache::archives=$APTROOT/cache/archives" -o APT::Get::List-Cleanup=0 -o APT::Update::Post-Invoke= -o APT::Update::Post-Invoke-Success=)
apt-get "${APT_OPTS[@]}" update
```

Скачайте зафиксированные пакеты (версии соответствуют проверенному snapshot репозиториев на 25 августа 2026 года):

```bash
set -euo pipefail
cd /workspace/1c-agent-harness
APTROOT="$PWD/.local/tools/aptroot"
APT_OPTS=(-o "Dir::Etc::sourcelist=$APTROOT/etc/apt/sources.list" -o Dir::Etc::sourceparts=- -o "Dir::State::lists=$APTROOT/state/lists" -o "Dir::Cache::archives=$APTROOT/cache/archives" -o APT::Get::List-Cleanup=0 -o APT::Update::Post-Invoke= -o APT::Update::Post-Invoke-Success=)
test ! -e .local/cache/debs
test ! -L .local/cache/debs
test ! -e .local/platform/libs
test ! -L .local/platform/libs
mkdir -p .local/cache/debs/trixie .local/cache/debs/bookworm
mkdir .local/platform/libs
TRIXIE_PKGS=(
  fontconfig-config=2.15.0-2.3 fonts-dejavu-core=2.37-8
  libatk-bridge2.0-0t64=2.56.2-1+deb13u1 libatk1.0-0t64=2.56.2-1+deb13u1
  libatspi2.0-0t64=2.56.2-1+deb13u1
  libavahi-client3=0.8-16 libavahi-common3=0.8-16
  libcairo2=1.18.4-1+b1
  libcairo-gobject2=1.18.4-1+b1 libgdk-pixbuf-2.0-0=2.42.12+dfsg-4+deb13u1
  libcups2t64=2.4.10-3+deb13u2 libdatrie1=0.2.13-3+b1
  libdbus-1-3=1.16.2-2 libdrm2=2.4.124-2 libelf1t64=0.192-4
  libfontconfig1=2.15.0-2.3 libfontenc1=1:1.1.8-1+b2
  libfreetype6=2.13.3+dfsg-1+deb13u1 libfribidi0=1.0.16-1
  libgbm1=25.0.7-2+deb13u1 libgl1=1.7.0-1+b2 libglib2.0-0t64=2.84.4-3~deb13u3
  libglx0=1.7.0-1+b2 libgraphite2-3=1.3.14-2+deb13u1
  libglu1-mesa=9.0.2-1.1+b3 libgtk-3-0t64=3.24.49-3
  libharfbuzz0b=10.2.0-1+deb13u1 libice6=2:1.1.1-1
  libpangocairo-1.0-0=1.56.3-1 libsoup-2.4-1=2.74.3-10.1
  libpango-1.0-0=1.56.3-1 libpixman-1-0=0.44.0-3
  libpng16-16t64=1.6.48-1+deb13u5 libsm6=2:1.2.6-1
  libthai0=0.1.29-2+b1 libwayland-client0=1.23.1-3 libwayland-server0=1.23.1-3
  libx11-6=2:1.8.12-1 libx11-xcb1=2:1.8.12-1 libxau6=1:1.0.11-1
  libxcb1=1.17.0-2+b1 libxcb-render0=1.17.0-2+b1 libxcb-shm0=1.17.0-2+b1
  libxcomposite1=1:0.4.6-1 libxdamage1=1:1.1.6-1+b2 libxdmcp6=1:1.1.5-1
  libxext6=2:1.3.4-1+b3 libxfixes3=1:6.0.0-2+b4
  libxfont2=1:2.0.6-1+deb13u1 libxi6=2:1.8.2-1
  libxkbcommon0=1.7.0-2 libxkbfile1=1:1.1.0-1+b4 libxmuu1=2:1.1.3-3+b4
  libxml2=2.12.7+dfsg+really2.9.14-2.1+deb13u3
  libxrandr2=2:1.5.4-1+b3 libxrender1=1:0.9.12-1 libxxf86vm1=1:1.1.4-1+b4
  x11-xkb-utils=7.7+9 xkb-data=2.42-1
  xauth=1:1.1.2-1.1 xserver-common=2:21.1.16-1.3+deb13u3
  xserver-xorg-core=2:21.1.16-1.3+deb13u3 xvfb=2:21.1.16-1.3+deb13u3
)
BOOKWORM_PKGS=(
  libabsl20220623=20220623.1-1+deb12u2 libaom3=3.6.0-1+deb12u2
  libasound2=1.2.8-1+b1
  libavif15=0.11.1-1+deb12u1 libcloudproviders0=0.3.1-2
  libdav1d6=1.0.0-2+deb12u1 libdw1=0.188-2.1
  libegl-mesa0=22.3.6-1+deb12u2 libegl1=1.6.0-1 libenchant-2-2=2.3.3-2
  libepoxy0=1.5.10-1 libevdev2=1.13.0+dfsg-1 libflite1=2.2-5
  libgav1-1=0.18.0-1+b1 libglvnd0=1.6.0-1
  libgstreamer-gl1.0-0=1.22.0-3+deb12u6
  libgstreamer-plugins-base1.0-0=1.22.0-3+deb12u6
  libgstreamer1.0-0=1.22.0-2+deb12u1 libgudev-1.0-0=237-2
  libharfbuzz-icu0=6.0.0+dfsg-3 libhyphen0=2.8.8-7
  libicu72=72.1-3+deb12u1 libjavascriptcoregtk-4.0-18=2.50.6-1~deb12u2
  libjpeg62-turbo=1:2.1.5-2 libmanette-0.2-0=0.2.6-3+b1
  libopengl0=1.6.0-1 liborc-0.4-0=1:0.4.33-2
  libpangoft2-1.0-0=1.50.12+ds-1 librav1e0=0.5.1-6
  libsecret-1-0=0.20.5-3 libsvtav1enc1=1.4.1+dfsg-1
  libunwind8=1.6.2-3 libwayland-cursor0=1.21.0-1 libwayland-egl1=1.21.0-1
  libwebkit2gtk-4.0-37=2.50.6-1~deb12u2
  libwebp7=1.2.4-0.2+deb12u1 libwebpdemux2=1.2.4-0.2+deb12u1
  libwebpmux3=1.2.4-0.2+deb12u1 libwoff1=1.0.2-2
  libxcursor1=1:1.2.1-1 libxinerama1=2:1.1.4-3
  libxslt1.1=1.1.35-1+deb12u4 libyuv0=0.0~git20230123.b2528b0-1
)
(
  cd .local/cache/debs/trixie
  apt-get "${APT_OPTS[@]}" download "${TRIXIE_PKGS[@]}"
)
(
  cd .local/cache/debs/bookworm
  apt-get "${APT_OPTS[@]}" download "${BOOKWORM_PKGS[@]}"
)
for package in .local/cache/debs/trixie/*.deb .local/cache/debs/bookworm/*.deb; do
  dpkg-deb -x "$package" .local/platform/libs
done
```

Список содержит 106 пакетов и в проверенном extraction занимает около 278 МБ. Он повторно собран в новый пустой каталог `.local/runs/bootstrap-order-verify/libs/` точно в опубликованном порядке (trixie, затем bookworm); `ldd` для `1cv8t`, Xvfb, `xauth` и `xkbcomp` не показал `not found`. Полный smoke на этом runtime (`bootstrap-order-smoke`) завершился process exit `0/0/0`, `/DumpResult` `0/0/0`, дал 5 099 файлов, 1 258 BSL и ожидаемый content ID.

Создайте fontconfig и writable cache:

```bash
set -euo pipefail
cd /workspace/1c-agent-harness
mkdir -p .local/cache/fontconfig
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
root = Path('/workspace/1c-agent-harness')
config = ET.Element('fontconfig')
ET.SubElement(config, 'dir').text = str(root / '.local/platform/libs/usr/share/fonts')
ET.SubElement(config, 'cachedir').text = str(root / '.local/cache/fontconfig')
ET.ElementTree(config).write(root / '.local/platform/fonts.conf', encoding='utf-8', xml_declaration=True)
PY
```

## 4. Установить системные XKB-компоненты

Xvfb вызывает абсолютный `/usr/bin/xkbcomp`. Два нужных системных `.deb` уже получены из подписанного Debian snapshot и распакованы локально; `libxkbfile1` остаётся в локальном runtime. Root-шаг копирует `.deb` в случайный root-owned staging, повторно проверяет hashes и публикует только `xkbcomp` и XKB data. Команда отказывается продолжать при любом существующем destination, включая dangling symlink:

```bash
docker exec -u root <container-id> bash -c 'set -euo pipefail; ROOT=/workspace/1c-agent-harness; DEBS="$ROOT/.local/cache/debs/trixie"; test ! -e /usr/bin/xkbcomp; test ! -L /usr/bin/xkbcomp; test ! -e /usr/share/X11/xkb; test ! -L /usr/share/X11/xkb; STAGE=$(mktemp -d /root/xkb-stage.XXXXXX); install -m 0600 "$DEBS/x11-xkb-utils_7.7+9_amd64.deb" "$STAGE/x11.deb"; install -m 0600 "$DEBS/xkb-data_2.42-1_all.deb" "$STAGE/xkb-data.deb"; printf "%s  %s\n" 745e29c79bb435d057cdbf8bb59a35fa33e818e566cb754674f44d381ccd4317 "$STAGE/x11.deb" 196ff18533382f64e057ea49df2bb486bd4275a4cc0917361edb560b8756dada "$STAGE/xkb-data.deb" | sha256sum -c -; install -d -m 0700 "$STAGE/root"; dpkg-deb -x "$STAGE/x11.deb" "$STAGE/root"; dpkg-deb -x "$STAGE/xkb-data.deb" "$STAGE/root"; install -m 0755 "$STAGE/root/usr/bin/xkbcomp" /usr/bin/xkbcomp; install -d -m 0755 /usr/share/X11; cp -a "$STAGE/root/usr/share/X11/xkb" /usr/share/X11/xkb; rm -f "$STAGE/x11.deb" "$STAGE/xkb-data.deb"; test "$(stat -c %u "$STAGE/root")" = 0; rm -rf --one-file-system "$STAGE/root"; rmdir "$STAGE"; test -x /usr/bin/xkbcomp; test -d /usr/share/X11/xkb; install -d -o root -g root -m 1777 /tmp/.X11-unix; echo XKB_READY'
```

## 5. Readiness gate

```bash
set -euo pipefail
cd /workspace/1c-agent-harness
V="$PWD/.local/platform/1cv8t/x86_64/8.5.1.1150"
L="$PWD/.local/platform/libs/usr/lib/x86_64-linux-gnu"
export LD_LIBRARY_PATH="$V:$L"
test -x "$V/1cv8t"
test -x .local/platform/libs/usr/bin/Xvfb
test -x .local/platform/libs/usr/bin/xvfb-run
test -x .local/platform/libs/usr/bin/xauth
test -x /usr/bin/xkbcomp
test -d /usr/share/X11/xkb
test -f .local/platform/fonts.conf
python3 -c 'from pathlib import Path; assert any(p.is_file() for p in Path(".local/platform/libs/usr/share/fonts").rglob("*"))'
check_ldd() {
  local output
  output=$(ldd "$1")
  if grep -Fq 'not found' <<<"$output"; then
    printf '%s\n' "$output" >&2
    return 1
  fi
}
check_ldd "$V/1cv8t"
check_ldd .local/platform/libs/usr/bin/Xvfb
check_ldd .local/platform/libs/usr/bin/xauth
check_ldd /usr/bin/xkbcomp
echo LAB_READY
```

`LAB_READY` подтверждает runtime, но не объявляет его автоматически доступным для project target.
CF-open использует одну executor-owned capability
`.local/capabilities/cf_to_hierarchical_snapshot` с контрактом `--source <immutable-cf>
--output <new-empty-snapshot> --work-root <owned-disposable-root>`. Она должна выполнить штатные
`CREATEINFOBASE` → `/LoadCfg` → `/DumpConfigToFiles -Format Hierarchical`, вернуть `0` только после
проверки всех `/DumpResult`, не изменять source и завершить все процессы. Harness сам проверяет
полученный closed tree, создаёт manifest, удаляет work root и только затем атомарно публикует
retained target. Конкретная capability является частью заранее подготовленного executor и не
скачивается, не устанавливается и не генерируется командой `open`.

После `LAB_READY` выполните fail-closed smoke из [runbook лаборатории](lab.md). После подготовки
capability публичная проверка выполняется одной командой `python3 scripts/project_target.py open`.

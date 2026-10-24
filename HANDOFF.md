# RP500 Studio — estado y traspaso

Editor no oficial de la DigiTech RP500 para Linux. Ver `README.md`. Este archivo sirve para retomar el trabajo en otra sesión.

## Reglas acordadas con el usuario
- **Pruebas de escritura en flash solo sobre el preset de usuario nº 100 «SCI FI»** (índice 99). Antes: respaldo (JSON).
- Editar el buffer de edición (RAM) para pruebas es seguro, pero dejar cada valor como estaba. Los parámetros de posición 26
  (ids 8706–8712) son lecturas vivas del pedal de expresión y cambian solos: no restaurarlos.
- El puerto `/dev/snd/midiC1D0` es exclusivo. Si una prueba falla con «Dispositivo ocupado» o se cuelga, es casi seguro que el
  usuario tiene `python3 run.py` abierto: **pedirle que la cierre, no matar el proceso**.
- Interfaz parecida a mk300_studio (`../mk300_studio`), funcionalidad como gdigi. Nativa de Linux, en Python/PyQt5.

## Protocolo (verificado en la pedalera)
SysEx `F0 00 00 10 <dev=7F> <5E> <05> <proc> <datos empaquetados 7 bits> <xor> F7`. Implementación en `rp500/protocol.py`.
Procedimientos: 01/02 identidad, 08/09 configuración, 21/22 nombres de banco, 2A→2B/2D/2C leer preset (START=banco,idx,nombre;
PARAMS = contador de 16 bits + (id16,pos,valor variable); END), 39 mover preset (guardar = buffer 4,0 → usuario n con nombre),
2B+2D enviar preset al buffer, 40/41 pedir/fijar parámetro, 3A/3B lista de parámetros asignables al pedal, 70 notificaciones.
Valores: <0x80 un byte; si no, `0x80|n` seguido de n bytes. Bancos: 0 sistema, 1 usuario, 4 buffer de edición.
Las tablas de efectos (`rp500/data/effects.json`, `modifiers.json`) se extrajeron de `effects.c` de gdigi compilándolo con un glib
simulado; el cambio de tipo hace que la pedalera reponga los valores por defecto del tipo nuevo (la app relee el preset).
Pedal de expresión: parámetro (8194, pos 19) = `(pos<<16)|id` del parámetro asignado; Min/Max = 8195/8196.
Bypass Amp/Cab: id 12361 (1 = bypass), compartido por los bloques Amp y Cab; polaridad deducida, no oída.

**Modo GUI (importante):** al conectar hay que fijar el parámetro 12298 (pos 0) = 1 y ponerlo a 0 al salir (`Pedal.gui_mode`).
Sin él la RP500 acepta las ediciones en su memoria (se leen de vuelta) pero no actualiza su panel ni LEDs. Confirmado por el usuario.
Los desplegables nativos de Qt se cierran al soltar el ratón en Wayland: usar `OverlayCombo` y diálogos propios (`SaveDialog`).

## Pendiente
1. Probar la sincronía de perillas movidas en la pedalera (señal `param_changed`) y los cambios de preset desde la pedalera.
2. Verificar por sonido el bypass de Amp/Cab y abrir un `.rp500p` creado por gdigi real.
3. Escala de ventana como en mk300; detectar cambios de banco (hoy solo el buffer de edición).
4. Repositorio: `git@github.com:fr33co/rp500_studio.git` (rama `main`, GPL-3.0 o posterior), con el ruleset «Protect main (owner only)»
   igual que mk300_studio (sin borrar `main`, sin reescribir historia, PR con 1 aprobación; el admin puede saltárselo).
   Antes de cada subida: `sh tools/check_refs.sh` (debe decir 0 archivos). `.git` vive en una carpeta sincronizada: riesgo de conflictos.

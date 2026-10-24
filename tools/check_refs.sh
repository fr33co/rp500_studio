#!/bin/sh
# Comprueba que lo versionado no contiene datos personales del equipo local (usuario y rutas del home).
# Los términos se arman por partes para que este script no se detecte a sí mismo.
a='aguada''rrama'; b='/home''/'
n=$(git grep -I -i -c -E "$a|$b" HEAD -- . ':!LICENSE' | wc -l)
echo "archivos con referencias en HEAD: $n"
[ "$n" -eq 0 ]

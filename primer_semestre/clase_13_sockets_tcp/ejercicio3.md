[127.0.0.1:37742] recv 13 bytes: b'HOLACOMOESTAS'
[127.0.0.1:37742] cerró tras 13 bytes

No, no viola el contrato de TCP.

TCP es un protocolo orientado a flujo de bytes, no conserva los límites de las llamadas a send() o sendall().


## ¿Por qué no puede ser simplemente sock.recv(n)?

recv(n) puede devolver menos de n bytes aunque todavía haya datos por recibir. Por eso recibir_exacto() debe repetir las llamadas a recv() hasta obtener exactamente n bytes o hasta que el otro extremo cierre la conexión.

## ¿Qué pasa si el mensaje contiene \n?

Sí, funciona perfectamente.

Por ejemplo:

enviar_mensaje(sock, b'hola\ncomo estas')

La longitud será:

15

y se manda:

[longitud = 15][hola\ncomo estas]

El receptor primero lee los 4 bytes:

cabecera = recibir_exacto(sock, 4)

obtiene:

longitud = 15

y después hace:

recibir_exacto(sock, 15)

Por lo tanto, el \n es simplemente otro byte del mensaje.

¿Y con la Parte B?

Ahí es diferente.

En la Parte B, \n es justamente el delimitador que indica el final del mensaje.

Entonces si mandamos:

hola
como estas

la versión de la Parte B interpreta:

mensaje 1 → hola
mensaje 2 → como estas

No puede considerar ese \n como parte del contenido del mensaje, porque \n tiene un significado especial: marca el final.

Diferencia fundamental

Parte B — delimitador:

hola\ncomo estas\n
    ↑
  termina

Parte C — longitud:

[15][hola\ncomo estas]
     ↑
     todo es contenido

Por eso el framing por longitud permite enviar cualquier byte, incluido \n, sin confundirlo con el final del mensaje.

## ¿Qué pasa con 0 bytes? ¿Y con 5 GB?
Mensaje de 0 bytes

Sí, se puede representar.

Mandaríamos:

enviar_mensaje(sock, b'')

La cabecera sería:

[00 00 00 00]

El receptor lee:

longitud = 0

y entonces:

recibir_exacto(sock, 0)

debería devolver:

b''

Es decir, tenemos un mensaje válido cuyo contenido tiene cero bytes.

# ¿Y un mensaje de 5 GB?

Acá aparece una limitación importante de este protocolo.

Estamos usando:

struct.pack('!I', len(payload))

!I significa unsigned integer de 32 bits.

Por lo tanto, podemos representar longitudes desde:

0

hasta:

4.294.967.295 bytes

aproximadamente 4 GiB.

Entonces 5 GB no entra en un campo de 4 bytes.

Si intentás:

struct.pack('!I', 5_000_000_000)

vas a obtener un error porque el número es demasiado grande para un entero sin signo de 32 bits.

Si necesitáramos soportar mensajes mayores, tendríamos que cambiar el protocolo, por ejemplo usando 8 bytes:

struct.pack('!Q', len(payload))

donde Q es un entero sin signo de 64 bits.

## Parte D

Comparación entre framing por delimitador y framing por longitud

| Característica | Delimitador | Longitud |
|---|---|---|
| Contenido binario arbitrario | ❌ No es ideal, porque el delimitador podría aparecer dentro de los datos | ✅ Sí, puede contener cualquier byte |
| Depurable con `nc` | ✅ Sí, es fácil de probar escribiendo los mensajes manualmente | ❌ Es más difícil, porque hay que enviar la longitud en formato binario |
| Hay que saber el tamaño antes | ❌ No | ✅ Sí |

**Framing por delimitador:** utiliza un carácter o secuencia especial para indicar dónde termina un mensaje. Por ejemplo, usando `\n`:

```text
hola\n
chau\n
```

# ¿Por qué HTTP combina delimitador y longitud?

HTTP utiliza un delimitador para indicar el final de los headers y una longitud para indicar el tamaño del cuerpo.

Los headers son texto y tienen una estructura que permite utilizar \r\n como delimitador. El final de todos los headers se indica mediante:

\r\n\r\n

Por ejemplo:

GET /index.html HTTP/1.1\r\n
Host: ejemplo.com\r\n
Content-Type: text/plain\r\n
Content-Length: 5\r\n
\r\n
hola!

Una vez que terminan los headers, Content-Length indica cuántos bytes tiene el cuerpo. Por ejemplo:

Content-Length: 5

significa que después de los headers se deben leer exactamente 5 bytes.

Esta combinación permite aprovechar las ventajas de ambos métodos:

Los headers se pueden procesar fácilmente utilizando delimitadores porque son texto.
El cuerpo puede contener cualquier tipo de información, incluso datos binarios, y Content-Length permite saber exactamente cuántos bytes hay que leer.
No es necesario buscar un carácter especial dentro del cuerpo para determinar dónde termina.
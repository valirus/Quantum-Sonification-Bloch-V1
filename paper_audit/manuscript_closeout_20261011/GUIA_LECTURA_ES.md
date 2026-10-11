# Cómo entender y defender este paper

El resultado científico es un instrumento cuya relación entre entradas y sonido se puede rastrear, comprobar y delimitar. Su valor no depende de afirmar que descubrimos nueva física fundamental.

## El flujo, con una analogía

El estado de 15 qubits es como una obra completa con 32.768 amplitudes complejas. Una reducción de un qubit es una vista de una parte: conserva lo que puede describirse mirando ese qubit solo, después de ignorar los demás. No es una proyección que deje intacta la obra completa.

Bloch describe esa vista local. La dirección controla frecuencia y posición estéreo; el radio controla amplitud y mezcla local. La información mutua describe relaciones por pares: es como saber cuánto depende una parte de otra, sin conservar todas las relaciones del conjunto. Puede incluir correlación clásica y cuántica. No es una medida exclusiva de entrelazamiento.

El bosque selecciona una red de enlaces fuertes para organizar voces. Es comparable a elegir un conjunto de caminos de un mapa: ayuda a recorrerlo, pero elimina caminos y no equivale al mapa completo. La raíz y las etiquetas importan.

BFS organiza voces por fronteras, como grupos que actúan simultáneamente. DFS las organiza de una en una. Además cambian envolventes, promedio y duración; por eso no atribuimos toda diferencia exclusivamente al orden de recorrido.

## Por qué la duración DFS es el hallazgo primario y qué significa

La duración ideal es `8,88 − 0,18 × componentes − 0,25 × suma de pesos del bosque`, en segundos. Es un mecanismo diseñado, no una ley nueva de información cuántica.

M1 aprende con profundidad y descriptores locales. M2 recibe además dos resúmenes del grafo completo. Al evaluar circuitos nuevos, estos resúmenes ayudan a anticipar el tiempo que produce la regla del bosque: 46,65 → 19,78 ms de error RMS. La reducción de MSE es 82,01 %. No significa que la duración se acorte un 82 % ni que un oyente distinga esa diferencia.

La analogía es una lista de tareas cuyo tiempo total depende de sumar sus tiempos. Cambiar el orden de tareas conserva el total aunque cambie la experiencia. Los 16.000 controles DFS comprueban exactamente esa invariancia. BFS depende también de agrupar tareas y de sus promedios: cambiar grupos puede cambiar el total.

## Qué añade la validación que no añade un valor p pequeño

El primer lote sirvió para formular y ajustar el análisis. El segundo se generó tras congelar el protocolo. Evaluarlo una vez prueba si el hallazgo sobrevive a circuitos nuevos de la misma familia. El resultado principal sobrevive; la asociación de distancias de información mutua/DFS no pasa la familia de validación. Conservar ese resultado negativo hace el argumento más preciso.

Las capas de una semilla son capítulos de la misma trayectoria, no once libros independientes. Se remuestrean libros completos: semillas. Las 4.950 parejas de distancias tampoco son 4.950 experimentos independientes, porque reutilizan los mismos 100 circuitos.

## Tres entropías diferentes

- **Entropía local:** mezcla de un qubit reducido. El estado completo puede seguir siendo puro.
- **Entropía del corte central:** entrelazamiento entre los bloques 7 y 8, para un estado global puro. Está entre 0 y 7 bits. Page da una media de estados aleatorios Haar, aproximadamente 6,63935, no un máximo obligatorio.
- **Entropía espectral:** distribución de potencia del sonido entre frecuencias. Su unidad matemática puede ser bits sin convertirse en entropía cuántica.

La escalera central aparece porque sólo ciertas capas cruzan el corte. Un cambio dentro de cada bloque puede reorganizarlo sin cambiar el entrelazamiento entre bloques. La escalera no implica cuantización de entropía, holografía ni espacio-tiempo emergente.

## La demostración de pérdida global

Construimos estados físicos donde todas las vistas de uno y dos qubits son iguales, pero el entrelazamiento entre los bloques cambia de 0 a 7 bits. El instrumento recibe las mismas entradas y produce el mismo audio por modo. Es como recibir siempre los mismos resúmenes de una obra mientras cambia una relación que esos resúmenes no describen. Ningún algoritmo que reciba sólo ese audio final puede reconstruir universalmente esa entropía; no es un problema que se resuelva entrenando más.

No contradice predecir bien duración en nuestra familia de circuitos. Predecir una consecuencia de una regla y recuperar un estado global son tareas distintas.

## Qué defender y qué no

Defendemos sensibilidad selectiva, reproducibilidad, predicción independiente, controles mecánicos y límites de información explícitos. No defendemos reconstrucción cuántica, preservación topológica completa, isometría, utilidad humana demostrada ni superioridad frente a otros instrumentos. La interfaz real puede hacer visibles estas correspondencias; documentarla no sustituye medir aprendizaje o usabilidad.

La fase experimental de este alcance puede cerrarse. El siguiente trabajo es editorial y documental, no perseguir otro resultado significativo.

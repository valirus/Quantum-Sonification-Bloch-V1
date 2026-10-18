import type { SonificationSeedAsset } from "./types";

export function ExampleLesson({ seed, layer }: { seed: SonificationSeedAsset; layer: number }) {
  const lesson = seed.lesson;
  if (!lesson) return null;
  const step = lesson.steps.find(item => item.layer === layer);
  return <section className="qs-panel qs-example-lesson" aria-label="Explicación del ejemplo didáctico">
    <div><div className="qs-kicker">Ejemplo didáctico · simulación exacta</div><h2>{lesson.question}</h2><p className="qs-example-step"><strong>Paso {layer} · {step?.label}</strong></p><p className="qs-muted">{step?.caption}</p></div>
    {step?.target_probability !== null && step?.target_probability !== undefined && <div className="qs-target-probability"><span>Probabilidad de medir {lesson.target_bitstring}</span><strong>{(100 * step.target_probability).toFixed(3)} %</strong><small>Del vector de estado; no se estima del sonido.</small></div>}
    <details className="qs-quiet-details"><summary>Qué se comprobó y qué significa</summary><p>Los estados y el audio se generaron con el código científico congelado. Bell y GHZ se contrastaron con sus vectores ideales; Grover se contrastó también con una construcción matricial y la fórmula de amplificación. La ejecución es ideal, sin ruido de dispositivo.</p><p>La colección ilustra el funcionamiento del sistema. No forma parte de las 200 semillas del estudio ni demuestra por sí sola aprendizaje o reconocimiento auditivo. Cada paso reproduce el estado al terminar su bloque: la animación no crea estados entre registros.</p><p>En Bell, la MI del par alcanza 2 bits; en GHZ, cada par tiene 1 bit. Ambos estados globales son puros y sus estados locales finales son mixtos. La dirección de un vector de Bloch nulo no está definida, por lo que se usa la voz neutral del motor.</p></details>
  </section>;
}

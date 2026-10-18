const NEUTRAL = [18, 21, 27];
const INCREASE = [239, 193, 123];
const DECREASE = [137, 195, 231];
const linear = (x: number) => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4;
const srgb = (x: number) => x <= .0031308 ? 12.92 * x : 1.055 * x ** (1 / 2.4) - .055;
export function colorFraction(value: number, maximum: number, logarithmic: boolean) {
  if (maximum <= 0) return 0;
  const magnitude = Math.min(maximum, Math.abs(value));
  return logarithmic ? Math.log1p(magnitude / 1e-6) / Math.log1p(maximum / 1e-6) : magnitude / maximum;
}
export function matrixColor(value: number, maximum: number, divergent: boolean, logarithmic: boolean) {
  const amount = colorFraction(value, maximum, logarithmic);
  const end = divergent && value < 0 ? DECREASE : INCREASE;
  const rgb = NEUTRAL.map((base, i) => Math.round(255 * srgb(linear(base / 255) * (1 - amount) + linear(end[i] / 255) * amount)));
  return `rgb(${rgb.join(",")})`;
}
export function luminance(color: string) {
  const rgb = color.match(/\d+/g)!.map(Number).map(v => linear(v / 255));
  return .2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2];
}

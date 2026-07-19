"use strict";

// ============================================================
// Datos de releases — cómo añadir una nueva
// ============================================================
// Cada fila es un array con este orden de campos:
//
//   [Release, Año, "Fecha PaP", "Mes", PaP Entrada, PaP Resueltas, Post Entrada, Post Resueltas]
//
//   Release        -> código de la release, formato "2026R7" (año + R + número).
//                     Mantén este patrón: el filtro por año del dashboard
//                     depende de que el año en el código y el campo Año coincidan.
//   Año            -> número, ej. 2026.
//   "Fecha PaP"    -> texto tipo "7-jun." (día-mes abreviado con punto).
//                     Puedes dejarlo como "" si aún no hay fecha; en ese caso
//                     el dashboard usará el nombre del mes como respaldo.
//   "Mes"          -> nombre del mes en español (Enero, Febrero, ...),
//                     solo se usa si "Fecha PaP" está vacío.
//   PaP Entrada    -> nº de incidencias entradas en PaP (entero).
//   PaP Resueltas  -> nº de esas incidencias resueltas en PaP (entero).
//   Post Entrada   -> nº de incidencias entradas en la 1ª semana post-PaP (entero).
//   Post Resueltas -> nº de esas incidencias resueltas (entero).
//
// Para incorporar una release nueva: añade una línea al final del array con
// estos 8 valores, guarda el fichero y recarga la página. No hace falta
// tocar nada más — el dashboard recalcula automáticamente el filtro de años,
// los KPIs, las gráficas (últimas 12 releases) y la tabla.
// ============================================================
const RAW_RELEASES = [
  ["R1", 2020, "9-feb.", "Febrero", 61, 46, 23, 17],
  ["R2", 2020, "1-mar.", "Marzo", 22, 18, 10, 9],
  ["R3", 2020, "29-mar.", "Marzo", 32, 26, 11, 9],
  ["R4", 2020, "26-abr.", "Abril", 53, 44, 5, 5],
  ["R6", 2020, "14-jun.", "Junio", 46, 36, 11, 9],
  ["R7", 2020, "2-ago.", "Agosto", 50, 32, 85, 70],
  ["R9", 2020, "27-sep.", "Septiembre", 49, 37, 71, 63],
  ["R11", 2020, "29-nov.", "Noviembre", 42, 36, 21, 17],
  ["2021R1", 2021, "31-ene.", "Enero", 61, 48, 30, 22],
  ["2021R3", 2021, "14-mar.", "Marzo", 42, 38, 10, 8],
  ["2021R4", 2021, "18-abr.", "Abril", 23, 19, 4, 4],
  ["2021R5", 2021, "16-may.", "Mayo", 44, 38, 12, 10],
  ["2021R6", 2021, "20-jun.", "Junio", 50, 43, 11, 11],
  ["2021R7", 2021, "1-ago.", "Julio", 46, 44, 25, 22],
  ["2021R9", 2021, "19-sep.", "Septiembre", 60, 50, 17, 14],
  ["2021R10", 2021, "17-oct.", "Octubre", 41, 32, 14, 9],
  ["2021R11", 2021, "28-nov.", "Noviembre", 49, 43, 31, 21],
  ["2022R1", 2022, "30-ene.", "Enero", 53, 41, 17, 12],
  ["2022R3", 2022, "13-mar.", "Marzo", 62, 56, 19, 16],
  ["2022R4", 2022, "18-abr.", "Abril", 54, 45, 21, 18],
  ["2022R6", 2022, "5-jun.", "Junio", 43, 36, 26, 22],
  ["2022R7", 2022, "31-ago.", "Julio", 77, 65, 86, 72],
  ["2022R9", 2022, "18-sep.", "Septiembre", 58, 48, 8, 7],
  ["2022R10", 2022, "23-oct.", "Octubre", 61, 55, 59, 48],
  ["2022R11", 2022, "27-nov.", "Noviembre", 59, 52, 16, 12],
  ["2023R2", 2023, "5-feb.", "Febrero", 86, 69, 31, 24],
  ["2023R3", 2023, "26-mar.", "Marzo", 95, 85, 39, 32],
  ["2023R5", 2023, "21-may.", "Mayo", 71, 62, 48, 34],
  ["2023R7", 2023, "23-jul.", "Julio", 118, 93, 73, 58],
  ["2023R9", 2023, "24-sep.", "Septiembre", 75, 68, 45, 36],
  ["2023R10", 2023, "15-oct.", "Octubre", 29, 28, 5, 5],
  ["2023R11", 2023, "26-nov.", "Noviembre", 128, 103, 83, 56],
  ["2024R1", 2024, "28-ene.", "Enero", 87, 75, 49, 42],
  ["2024R4", 2024, "7-abr.", "Abril", 78, 77, 36, 28],
  ["2024R6", 2024, "9-jun.", "Junio", 54, 50, 36, 33],
  ["2024R7", 2024, "21-jul.", "Julio", 60, 54, 54, 46],
  ["2024R9", 2024, "22-sep.", "Septiembre", 85, 72, 47, 42],
  ["2024R10", 2024, "13-oct.", "Octubre", 15, 14, 6, 6],
  ["2024R11", 2024, "", "Diciembre", 53, 49, 17, 14],
  ["2025R2", 2025, "2-feb.", "Febrero", 64, 53, 48, 46],
  ["2025R3", 2025, "16-mar.", "marzo", 48, 41, 37, 31],
  ["2025R5", 2025, "11-may.", "mayo", 38, 34, 31, 25],
  ["2025R6", 2025, "8-jun.", "Junio", 13, 11, 2, 2],
  ["2025R7", 2025, "20-jul.", "Julio", 49, 44, 24, 17],
  ["2025R9", 2025, "21-sep.", "Septiembre", 52, 39, 64, 57],
  ["2025R11", 2025, "23-nov.", "Noviembre", 39, 34, 34, 28],
  ["2026R1", 2026, "15-feb.", "Febrero", 58, 50, 23, 23],
  ["2026R3", 2026, "15-mar.", "Marzo", 55, 46, 26, 26],
  ["2026R4", 2026, "26-abr.", "Abril", 43, 37, 28, 26],
  ["2026R6", 2026, "7-jun.", "Junio", 53, 46, 38, 33],
  ["2026R7", 2026, "7-jun.", "Junio", 0, 0, 0, 0],
];

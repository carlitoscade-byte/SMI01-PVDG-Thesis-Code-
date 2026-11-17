# Parámetros utilizados en la tesis

Este documento resume los principales parámetros utilizados en los algoritmos desarrollados para la tesis de maestría:

**“Evaluación del impacto de la generación distribuida fotovoltaica sobre la demanda del alimentador SMI-01 de la ANDE mediante la superposición de perfiles de generación y demanda.”**

Autor: **Carlos A. Domínguez E.**  
Universidad Nacional de Asunción – Facultad de Ingeniería  
Paraguay, 2026.

## 1. Área de estudio

El análisis corresponde al área de cobertura del alimentador **SMI-01 de la Administración Nacional de Electricidad (ANDE)**, localizada principalmente en el barrio Ciudad Nueva de Asunción, Paraguay.

Para la geocodificación del área de estudio, el script `pv_capacity_by_neighborhood2.py` utiliza como configuración por defecto:

| Parámetro | Valor |
|---|---|
| Área de búsqueda | Ciudad Nueva, Asunción, Paraguay |
| Fuente geoespacial por defecto | OpenStreetMap / Overpass |
| Fuente alternativa | Microsoft Building Footprints |
| Unidad espacial de análisis | Edificación / cubierta |

## 2. Parámetros del modelo geoespacial fotovoltaico

Los principales parámetros adoptados en la metodología de la tesis son los siguientes:

| Parámetro | Valor adoptado |
|---|---:|
| Potencia nominal por módulo | 0,41 kWp |
| Dimensiones del módulo | 1,10 m × 1,80 m |
| Separación mínima entre módulos | 0,02 m |
| Margen de seguridad (*setback*) | 0,60 m |
| Superficie mínima de cubierta | 5,0 m² |
| Elevación solar de referencia para análisis de sombras | 30° |
| Rendimiento específico anual | 1.650 kWh/kWp·año |

La potencia instalada no se determina mediante una densidad fija de potencia por unidad de superficie. El algoritmo realiza una disposición geométrica explícita de módulos sobre la superficie útil de cada cubierta y calcula posteriormente:

\[
P_{inst}=N_{mod}\times P_{mod}
\]

donde:

- \(P_{inst}\) es la potencia nominal instalada;
- \(N_{mod}\) es el número de módulos instalables;
- \(P_{mod}\) es la potencia nominal por módulo.

## 3. Parámetros geométricos adicionales del script

El script permite evaluar diferentes orientaciones e inclinaciones para determinar la configuración de módulos sobre las cubiertas.

Los valores por defecto incluidos en la versión utilizada son:

| Parámetro | Valor |
|---|---:|
| Inclinación mínima evaluada | 30° |
| Inclinación máxima evaluada | 60° |
| Paso de inclinación | 5° |
| Paso de barrido de orientación | 5° |
| Radio de búsqueda de edificaciones vecinas para sombreado | 40 m |
| Número máximo de vecinos evaluados | 60 |

Estos valores forman parte de la configuración computacional del algoritmo y pueden modificarse mediante argumentos de ejecución.

## 4. Estimación de energía anual

Para la estimación anual se utiliza el rendimiento específico:

\[
Y_{esp}=1.650\ \text{kWh/kWp·año}
\]

adoptado tomando como referencia el valor de **PVOUT para el área de Asunción del Global Solar Atlas**, desarrollado por Solargis para el World Bank Group.

La energía anual se calcula mediante:

\[
E_{FV}=P_{inst}\times Y_{esp}
\]

donde:

- \(E_{FV}\) es la energía fotovoltaica anual estimada;
- \(P_{inst}\) es la capacidad fotovoltaica nominal instalada;
- \(Y_{esp}\) es el rendimiento específico anual.

El rendimiento específico ya representa el desempeño global esperado del sistema. Por este motivo, el Performance Ratio (PR) **no se multiplica nuevamente** en la estimación anual.

## 5. Nota sobre el parámetro Performance Ratio del script

El archivo `pv_capacity_by_neighborhood2.py` conserva un parámetro denominado `performance_ratio` con un valor por defecto de `0.22`.

Este parámetro forma parte de la configuración histórica del script, pero **no interviene en el cálculo anual utilizado para los resultados de la tesis**, debido a que la energía anual se obtiene directamente mediante:

\[
E_{FV}=P_{inst}\times Y_{esp}
\]

Por tanto, no debe interpretarse el valor `0.22` como el PR efectivo utilizado para calcular los 11,97 GWh/año reportados en la tesis.

## 6. Resultados principales del análisis geoespacial

El procesamiento geoespacial permitió obtener los siguientes resultados para el escenario de máxima penetración:

| Indicador | Resultado |
|---|---:|
| Número total de módulos | 17.701 |
| Potencia fotovoltaica nominal potencial | 7.257,41 kWp |
| Potencia nominal equivalente | ≈ 7,26 MWp |
| Rendimiento específico | 1.650 kWh/kWp·año |
| Energía anual estimada | 11.974.726,5 kWh/año |
| Energía anual equivalente | ≈ 11,97 GWh/año |

La potencia aproximada de **6,30 MW** utilizada en los perfiles horarios corresponde al máximo valor de generación fotovoltaica estimado durante la simulación y no a la potencia nominal instalada.

## 7. Parámetros del procesamiento de irradiancia solar

El script `solar_irradiance_region.py` utiliza la siguiente configuración de referencia:

| Parámetro | Valor |
|---|---|
| Ciudad | Asunción |
| Latitud | −25,2637 |
| Longitud | −57,5759 |
| Zona horaria | America/Asuncion |
| Fuente principal utilizada | Open-Meteo |
| Fecha inicial configurada | 2024-01-01 |
| Fecha final configurada | 2024-12-31 |
| Año final de proyección | 2030 |

El script admite además NSRDB y PVGIS como fuentes alternativas. Sin embargo, para los resultados principales presentados en la tesis se utilizó **Open-Meteo** como fuente de las series históricas de irradiancia.

## 8. Variables solares procesadas

Las principales variables procesadas son:

| Variable | Descripción |
|---|---|
| GHI | Irradiancia global horizontal |
| DNI | Irradiancia directa normal |
| DHI | Irradiancia difusa horizontal |

A partir de estas variables se generan:

- perfiles horarios;
- valores diarios;
- valores mensuales;
- perfiles estacionales;
- climatologías mensuales;
- proyecciones hasta el año 2030.

## 9. Clasificación estacional

Para Paraguay, localizado en el hemisferio sur, se utiliza la siguiente agrupación:

| Estación | Meses |
|---|---|
| Verano | diciembre, enero y febrero |
| Otoño | marzo, abril y mayo |
| Invierno | junio, julio y agosto |
| Primavera | septiembre, octubre y noviembre |

## 10. Observaciones de reproducibilidad

Los parámetros incluidos en este documento corresponden a los valores utilizados o configurados en los algoritmos asociados a la tesis.

Los datos operativos del alimentador SMI-01 pertenecientes a la ANDE no se incluyen necesariamente en el repositorio cuando están sujetos a restricciones institucionales.

El código fuente completo se encuentra disponible en la carpeta `src/` del repositorio.

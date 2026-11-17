# Metodología de la investigación

Este documento resume la metodología implementada en la tesis de maestría:

**“Evaluación del impacto de la generación distribuida fotovoltaica sobre la demanda del alimentador SMI-01 de la ANDE mediante la superposición de perfiles de generación y demanda.”**

Autor: **Carlos A. Domínguez E.**  
Universidad Nacional de Asunción – Facultad de Ingeniería  
Paraguay, 2026.

## 1. Enfoque metodológico

La investigación adopta un enfoque **cuantitativo**, de carácter **aplicado**, mediante un **estudio de caso** centrado en el alimentador de distribución SMI-01 de la Administración Nacional de Electricidad (ANDE), ubicado en Asunción, Paraguay.

La metodología integra:

- análisis geoespacial de edificaciones y superficies de cubierta;
- estimación del potencial fotovoltaico instalable;
- procesamiento de información de irradiancia solar;
- modelación horaria y estacional de la generación fotovoltaica;
- análisis de la curva de demanda del alimentador;
- superposición temporal de generación y demanda;
- evaluación de distintos escenarios de penetración de PVDG;
- cuantificación de la reducción efectiva de la demanda máxima;
- estimación de energía hidroeléctrica desplazada;
- evaluación económica mediante costo evitado;
- comparación con el ingreso no percibido por la empresa distribuidora.

## 2. Unidad y área de análisis

La unidad principal de análisis corresponde al alimentador de distribución **SMI-01 de la ANDE** y al área urbana comprendida dentro de su zona de cobertura.

El universo de estudio comprende:

- edificaciones;
- superficies de techos;
- perfiles de demanda eléctrica;
- condiciones del recurso solar;
- generación fotovoltaica potencial.

El área urbana analizada corresponde principalmente al barrio Ciudad Nueva de Asunción, Paraguay.

## 3. Fuentes de información

La metodología integra información proveniente de distintas fuentes.

### 3.1 Información geoespacial

Para la identificación y caracterización de edificaciones se utilizan:

- OpenStreetMap;
- Nominatim;
- Overpass API;
- Microsoft Building Footprints.

Estas fuentes permiten obtener geometrías de edificaciones y delimitar las superficies de cubierta comprendidas dentro del área de estudio.

### 3.2 Información solar

Las series históricas y perfiles horarios de irradiancia utilizados para la modelación fueron procesados mediante **Open-Meteo**.

El script admite adicionalmente NSRDB y PVGIS como fuentes alternativas, aunque estas no corresponden a la configuración principal utilizada para obtener los resultados presentados en la tesis.

El **Global Solar Atlas**, desarrollado por Solargis para el World Bank Group, se utiliza como referencia para el rendimiento específico anual adoptado en la estimación energética.

### 3.3 Información de demanda

Los perfiles de demanda corresponden a datos horarios reales del alimentador SMI-01 suministrados por la ANDE.

Estos datos constituyen la referencia para evaluar la interacción temporal entre generación fotovoltaica y demanda eléctrica.

## 4. Procesamiento geoespacial

El procesamiento geoespacial se realiza mediante el script:

`src/pv_capacity_by_neighborhood2.py`

El procedimiento general comprende:

1. delimitación del área de estudio;
2. obtención de las geometrías de las edificaciones;
3. transformación de coordenadas geográficas a un sistema métrico adecuado;
4. cálculo de superficies de cubierta;
5. aplicación de márgenes de seguridad o *setbacks*;
6. exclusión de superficies inferiores al límite mínimo establecido;
7. evaluación aproximada del sombreado producido por edificaciones vecinas;
8. evaluación de diferentes orientaciones e inclinaciones de los módulos;
9. disposición geométrica de paneles sobre la superficie útil;
10. selección de la configuración que maximiza la cantidad de módulos instalables;
11. cálculo de la potencia fotovoltaica nominal correspondiente a cada edificación;
12. agregación de los resultados para el área completa de estudio.

La potencia nominal se determina mediante:

\[
P_{inst}=N_{mod}\times P_{mod}
\]

donde:

- \(P_{inst}\) es la potencia fotovoltaica nominal instalada;
- \(N_{mod}\) es el número de módulos instalables;
- \(P_{mod}\) es la potencia nominal individual de cada módulo.

El cálculo efectivo no utiliza una densidad fija de potencia por unidad de superficie, sino la disposición geométrica explícita de módulos sobre cada cubierta.

## 5. Estimación de la energía fotovoltaica anual

La energía anual se estima a partir de la capacidad nominal instalada y del rendimiento específico anual:

\[
E_{FV}=P_{inst}\times Y_{esp}
\]

donde:

- \(E_{FV}\) es la energía fotovoltaica anual estimada;
- \(P_{inst}\) es la potencia nominal instalada;
- \(Y_{esp}\) es el rendimiento específico anual.

Para la investigación se adoptó:

\[
Y_{esp}=1.650\ \text{kWh/kWp·año}
\]

tomando como referencia el valor de PVOUT correspondiente al área de Asunción del Global Solar Atlas.

El rendimiento específico incorpora el desempeño global esperado del sistema, por lo que el Performance Ratio no se multiplica nuevamente en esta estimación anual.

## 6. Procesamiento de irradiancia solar

El procesamiento del recurso solar se realiza mediante:

`src/solar_irradiance_region.py`

El procedimiento comprende:

1. definición de la ubicación del área de estudio;
2. descarga de las series horarias de irradiancia;
3. procesamiento de GHI, DNI y DHI;
4. conversión de las series a la zona horaria local;
5. generación de perfiles horarios;
6. cálculo de valores diarios;
7. agregación mensual;
8. agrupación estacional;
9. construcción de climatologías mensuales;
10. generación de proyecciones hasta el año 2030.

Las estaciones utilizadas corresponden al hemisferio sur:

- verano: diciembre, enero y febrero;
- otoño: marzo, abril y mayo;
- invierno: junio, julio y agosto;
- primavera: septiembre, octubre y noviembre.

## 7. Modelación de la generación fotovoltaica

Los perfiles de generación fotovoltaica se construyen considerando la capacidad instalada correspondiente a cada escenario y la variación temporal del recurso solar.

La generación fotovoltaica presenta valores nulos durante las horas nocturnas, aumenta durante la mañana, alcanza sus mayores valores en torno al periodo de mayor disponibilidad solar y disminuye hacia el final de la tarde.

La máxima potencia fotovoltaica obtenida en los perfiles simulados no debe interpretarse como potencia nominal instalada ni como potencia firme.

En el escenario de máxima penetración:

- la capacidad nominal estimada es aproximadamente **7,26 MWp**;
- la máxima potencia fotovoltaica observada en los perfiles simulados es aproximadamente **6,30 MW**.

## 8. Escenarios de penetración de PVDG

La capacidad fotovoltaica potencial máxima constituye la referencia para construir los siguientes escenarios:

| Escenario | Penetración |
|---|---:|
| Escenario 1 | 10 % |
| Escenario 2 | 20 % |
| Escenario 3 | 30 % |
| Escenario 4 | 50 % |
| Escenario 5 | 100 % |

Estos porcentajes representan fracciones de la capacidad fotovoltaica potencial estimada mediante el análisis geoespacial.

Los escenarios permiten comparar el comportamiento del alimentador bajo distintos niveles de incorporación de generación distribuida.

## 9. Superposición de generación y demanda

El análisis técnico se realiza mediante la superposición temporal de los perfiles horarios de demanda del alimentador y generación fotovoltaica.

La demanda neta puede expresarse mediante:

\[
P_{net}(t)=P_D(t)-P_{FV,util}(t)
\]

donde:

- \(P_{net}(t)\) es la demanda neta del alimentador;
- \(P_D(t)\) es la demanda original;
- \(P_{FV,util}(t)\) es la potencia fotovoltaica utilizada dentro del intervalo.

Para evitar valores negativos cuando la generación fotovoltaica supera la demanda, la generación utilizada puede expresarse como:

\[
P_{FV,util}(t)=\min[P_{FV}(t),P_D(t)]
\]

El análisis horario permite determinar:

- demanda neta;
- demanda máxima neta;
- hora del nuevo pico;
- desplazamiento temporal del pico;
- reducción efectiva de la demanda máxima;
- nivel de utilización de la capacidad nominal del alimentador;
- existencia o ausencia de excedentes de generación.

## 10. Reducción efectiva de la demanda máxima

La reducción del pico no se determina directamente a partir de la máxima potencia fotovoltaica.

Se obtiene comparando el máximo valor de la curva original de demanda con el máximo valor de la curva neta resultante:

\[
\Delta P_{max}=P_{max,original}-P_{max,neta}
\]

Esto permite distinguir entre:

- potencia fotovoltaica máxima disponible;
- reducción horaria de demanda;
- reducción efectiva del máximo del alimentador.

La diferencia es relevante porque la máxima generación fotovoltaica y la máxima demanda no necesariamente ocurren durante el mismo intervalo horario.

## 11. Cargabilidad del alimentador

La capacidad nominal del alimentador SMI-01 utilizada como referencia es:

\[
P_{nom}=13,6\ \text{MW}
\]

El nivel de utilización se determina comparando la demanda máxima con dicha capacidad nominal.

Este indicador se calcula para la condición original y para cada escenario de integración fotovoltaica.

## 12. Energía hidroeléctrica desplazada

La energía fotovoltaica coincidente con la demanda se interpreta como energía que deja de ser suministrada por las fuentes hidroeléctricas del sistema consideradas en la investigación, principalmente ITAIPU y YACYRETÁ.

La cuantificación se realiza de forma horaria, considerando únicamente la energía fotovoltaica efectivamente coincidente con la demanda del alimentador.

La energía desplazada constituye el vínculo entre el análisis técnico y la evaluación económica.

## 13. Evaluación económica

La evaluación económica se realiza desde la perspectiva de la empresa distribuidora y se basa en el concepto de **costo evitado de generación**.

El costo evitado se determina mediante la valorización de la energía hidroeléctrica desplazada utilizando el costo horario correspondiente a la energía proveniente de ITAIPU y YACYRETÁ.

De forma conceptual:

\[
C_{ev}=\sum_t E_{despl}(t)\times C_{unit}(t)
\]

donde:

- \(C_{ev}\) es el costo evitado;
- \(E_{despl}(t)\) es la energía hidroeléctrica desplazada en el intervalo \(t\);
- \(C_{unit}(t)\) es el costo unitario de la energía en dicho intervalo.

La evaluación también considera el **ingreso no percibido por la ANDE**, asociado a la reducción de energía vendida como consecuencia de la generación distribuida.

La comparación entre costo evitado e ingreso no percibido constituye un indicador económico parcial desde la perspectiva de la empresa distribuidora y **no representa un balance económico integral de la generación distribuida**.

No se realiza en esta investigación una evaluación del LCOE ni un análisis completo de CAPEX, OPEX o rentabilidad financiera desde la perspectiva del propietario de los sistemas fotovoltaicos.

## 14. Comparación de escenarios

Los escenarios de 10 %, 20 %, 30 %, 50 % y 100 % se comparan utilizando los siguientes indicadores:

- capacidad fotovoltaica instalada;
- generación fotovoltaica;
- demanda neta;
- demanda máxima neta;
- reducción efectiva del pico;
- cargabilidad del alimentador;
- energía hidroeléctrica desplazada;
- costo evitado;
- ingreso no percibido.

El propósito de esta comparación es identificar cómo varían los efectos técnicos y económicos a medida que aumenta la penetración de PVDG.

La metodología no pretende determinar un nivel óptimo definitivo de penetración, ya que dicha determinación requeriría estudios eléctricos complementarios, incluyendo análisis detallados de flujo de potencia, tensión, protecciones y capacidad de alojamiento de la red.

## 15. Herramientas utilizadas

Las principales herramientas empleadas son:

- Python;
- `pv_capacity_by_neighborhood2.py`;
- `solar_irradiance_region.py`;
- OpenStreetMap;
- Microsoft Building Footprints;
- Open-Meteo;
- Global Solar Atlas;
- Microsoft Excel;
- datos operativos del alimentador SMI-01 suministrados por la ANDE.

## 16. Flujo metodológico resumido

El procedimiento completo puede resumirse de la siguiente manera:

```text
Delimitar área de estudio
        ↓
Obtener edificaciones y geometrías de cubiertas
        ↓
Procesar superficies útiles
        ↓
Aplicar restricciones geométricas y sombreado
        ↓
Ubicar módulos fotovoltaicos
        ↓
Estimar capacidad nominal potencial
        ↓
Procesar recurso solar
        ↓
Construir perfiles de generación fotovoltaica
        ↓
Definir escenarios 10–20–30–50–100 %
        ↓
Superponer generación y demanda
        ↓
Calcular demanda neta y reducción efectiva del pico
        ↓
Cuantificar energía hidroeléctrica desplazada
        ↓
Calcular costo evitado
        ↓
Comparar con ingreso no percibido
        ↓
Comparar escenarios
```

## 17. Alcance y limitaciones

La metodología evalúa principalmente la interacción energética y temporal entre generación fotovoltaica distribuida y demanda del alimentador.

El estudio no incluye una simulación eléctrica detallada de:

- flujos de potencia en cada tramo;
- variaciones de tensión nodo a nodo;
- pérdidas técnicas detalladas;
- coordinación de protecciones;
- estabilidad dinámica;
- calidad de energía;
- capacidad de alojamiento mediante modelos eléctricos completos.

Por este motivo, los resultados deben interpretarse como una evaluación técnico-energética y económica del efecto de la PVDG sobre el alimentador SMI-01 dentro del alcance definido en la tesis.

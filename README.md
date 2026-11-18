# SMI01-PVDG-Thesis-Code

Código fuente utilizado en la tesis de maestría:

**“Evaluación del impacto de la generación distribuida fotovoltaica sobre la demanda del alimentador SMI-01 de la ANDE mediante la superposición de perfiles de generación y demanda.”**

Autor: **Carlos A. Domínguez E.**  
Universidad Nacional de Asunción – Facultad de Ingeniería  
Maestría en Energía para el Desarrollo Sostenible, Energías Renovables y Eficiencia Energética  
Paraguay, 2026.

## Descripción

Este repositorio contiene los algoritmos desarrollados y utilizados para el análisis geoespacial, la estimación del potencial fotovoltaico urbano y el procesamiento del recurso solar correspondiente al área de cobertura del alimentador SMI-01 de la Administración Nacional de Electricidad (ANDE), ubicado en Asunción, Paraguay.

Los códigos forman parte de la metodología utilizada para evaluar la integración de generación distribuida fotovoltaica (PVDG) en una red urbana de distribución.

## Scripts principales

### `pv_capacity_by_neighborhood2.py`

Script desarrollado para estimar la capacidad fotovoltaica potencialmente instalable en cubiertas urbanas.

El algoritmo realiza, entre otras, las siguientes operaciones:

- identificación y procesamiento de edificaciones;
- análisis de geometrías de cubiertas;
- transformación de sistemas de coordenadas;
- aplicación de márgenes de seguridad o *setbacks*;
- exclusión de superficies no aprovechables;
- análisis aproximado de sombreado;
- evaluación de orientación e inclinación de módulos;
- disposición geométrica de paneles fotovoltaicos;
- cálculo del número de módulos instalables;
- estimación de la potencia fotovoltaica nominal en kWp;
- estimación de la producción energética anual.

Para el estudio del alimentador SMI-01 se utilizó como configuración de referencia una capacidad fotovoltaica nominal máxima aproximada de **7,26 MWp**.

### `solar_irradiance_region.py`

Script utilizado para obtener y procesar series temporales de irradiancia solar correspondientes a Asunción, Paraguay.

Para los resultados principales de la tesis se utilizó **Open-Meteo** como fuente de las series históricas de irradiancia.

El algoritmo procesa:

- irradiancia global horizontal (GHI);
- irradiancia directa normal (DNI);
- irradiancia difusa horizontal (DHI);
- perfiles horarios;
- valores diarios;
- valores mensuales;
- perfiles estacionales;
- climatologías mensuales;
- proyecciones hasta el año 2030.

El código admite además otras fuentes de datos, como NSRDB y PVGIS, aunque estas alternativas no corresponden a la configuración principal utilizada para los resultados de la tesis.

## Parámetros principales del modelo geoespacial

| Parámetro | Valor |
|---|---:|
| Potencia nominal por módulo | 0,41 kWp |
| Dimensiones del módulo | 1,10 m × 1,80 m |
| Separación mínima entre módulos | 0,02 m |
| Margen de seguridad (*setback*) | 0,60 m |
| Superficie mínima de cubierta | 5,0 m² |
| Elevación solar de referencia para análisis de sombras | 30° |
| Rendimiento específico anual | 1.650 kWh/kWp·año |

El rendimiento específico anual fue adoptado tomando como referencia el valor de PVOUT correspondiente al área de Asunción obtenido del Global Solar Atlas.

## Área de estudio

El área analizada corresponde a la zona de cobertura del alimentador **SMI-01 de la ANDE**, ubicada principalmente en el barrio Ciudad Nueva de Asunción, Paraguay.

## Fuentes de información

Entre las principales fuentes de información utilizadas se encuentran:

- OpenStreetMap;
- Microsoft Building Footprints;
- Open-Meteo;
- Global Solar Atlas;
- datos de demanda del alimentador SMI-01 suministrados por la ANDE.

## Reproducibilidad

Los scripts disponibles en este repositorio corresponden a las herramientas utilizadas en la metodología de la tesis.

Los datos operativos pertenecientes a la ANDE que puedan estar sujetos a restricciones institucionales o de confidencialidad no se incluyen necesariamente en este repositorio. El código puede ejecutarse con conjuntos de datos equivalentes que respeten la estructura de entrada requerida.

## Versión

La versión destinada a respaldar la tesis será publicada como:

**v1.0.0 – Thesis version**

Esta versión será posteriormente archivada en un repositorio de preservación científica con DOI permanente.

## Licencia

Este software se distribuye bajo la Licencia MIT. Consulte el archivo LICENSE para obtener más detalles.

## Citación

Este software es archivado en Zenodo:
DOI: 10.5281/zenodo.24341850

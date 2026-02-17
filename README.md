# 🚦 DGT Traffic para Home Assistant

> [!IMPORTANT]
> **ESTADO DEL PROYECTO: VERSIÓN ESTABLE 1.2.1**  
> La integración ha alcanzado su primera versión estable.  
> Los módulos principales son funcionales y el proyecto entra ahora en fase de mantenimiento y mejora continua.

---
# v1.2.1 – Primera versión estable

* **Tres modos de Geolocalización**
* **Geolocalización dinámica mediante Persona**
* **Geolocalización mediante coordenadas**
* **Geolocalización mediante sensor de HA**
* **Nuevo device agrupando sensores de incidencias**
* **Config Flow modular completo**
* **Arquitectura refactorizada**
* **Dos módulos operativos (Incidencias + Electrolineras)**
* **Preparada para HACS**

---

## 💡 Sobre el Proyecto

**DGT Traffic** es una integración avanzada y modular para Home Assistant que permite la monitorización geolocalizada en tiempo real de:

- 🚧 Incidencias de tráfico  
- ⚡ Electrolineras / puntos de carga eléctrica  
- 🌧️ Eventos meteorológicos (en desarrollo)

Los datos provienen directamente de la **Dirección General de Tráfico (DGT)** mediante feeds oficiales DATEX2/XML.

Este proyecto nace para cubrir un vacío en la comunidad española de Home Assistant, ofreciendo un control granular basado en radio geográfico real, algo que hasta ahora no existía con este nivel de precisión.

---

## 🧩 Arquitectura Modular

La integración está dividida en módulos independientes que pueden configurarse múltiples veces:

### 🚧 Incidencias de Tráfico

- Accidentes
- Retenciones
- Obras
- Eventos especiales

Incluye:

- Geolocalización por HA / coordenadas / persona
- Clasificación por severidad
- Sensores agregados
- Entidades individuales
- Visualización directa en mapa

---

### ⚡ Electrolineras

- Filtrado por radio configurable
- Coordenadas automáticas, manuales o por persona
- Sensores agregados (totales, cercanas, potencia, etc.)
- Entidades dinámicas por estación
- Clasificación por rangos de potencia
- Visualización directa en mapa

---

## ✨ Características principales

- 📍 Geolocalización automática, manual o mediante Persona
- 📏 Cálculo real de distancia mediante `geopy`
- 🧭 Filtrado por radio configurable
- 🔌 Parsing completo DATEX2
- 🗺️ Soporte para visualización directa en mapa
- 📊 Sensores agregados + entidades individuales
- 🧠 Coordinadores y arquitectura limpia orientada a escalabilidad

---

## 🛠️ Instalación

Disponible mediante HACS como repositorio personalizado.

**Instalación mediante HACS:**

1. Añadir repositorio personalizado: https://github.com/Javisen/dgt_traffic
2. Reiniciar Home Assistant
3. Añadir integración DGT Traffic

**Instalación manual:**

1. Copiar la carpeta `dgt_traffic` dentro de: `config/custom_components/`

2. Reiniciar Home Assistant

Dependencias requeridas:

- `geopy`
- `xmltodict`

---

## 🗺️ Ejemplo de tarjeta de mapa (Electrolineras)

```yaml
type: panel
title: Electrolineras-Map
path: electrolineras-map
sections: []
cards:
  - type: custom:auto-entities
    card:
      type: custom:map-card
      preferCanvas: false
      height: 600px
    filter:
      include:
        - options: {}
          domain: sensor
          attributes:
            power_range: "*"
```
## 🗺️ Ejemplo de tarjeta de mapa (Incidencias)

```yaml
type: panel
title: Incidencias-DGT
path: incidencias-map
sections: []
cards:
  - type: custom:auto-entities
    card:
      type: custom:map-card
      height: 600px
    filter:
      include:
        - domain: sensor
          attributes:
            severity: "*"
```
---

## 🧪 Estado actual

- **Electrolineras**: estable  
- **Incidencias**: estable  
- **Frontend**: ejemplos incluidos  

---

## 🐞 Reporte de errores

Se aceptan Issues.

Por favor incluye:

- Versión de Home Assistant  
- Logs relevantes  
- Qué módulo falla (incidencias / electrolineras)  
- Ubicación aproximada o coordenadas (si aplica)  

Esto ayuda enormemente a mejorar la integración.

---

## ⚖️ Derechos Reservados y Licencia

Este software es obra original de **Javisen**.

Copyright (c) 2026 Javisen  
Distribuido bajo la Licencia MIT.

Aunque la licencia permite el uso del código, se hace constar que la idea original, la estructura de filtrado geográfico y la implementación técnica son propiedad intelectual del autor.

Se agradece respetar la autoría y esperar a versiones oficiales antes de realizar forks públicos.

---

Desarrollado con ❤️ en España para la comunidad de Home Assistant.

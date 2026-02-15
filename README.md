# 🚦 DGT Traffic (Pro) para Home Assistant

> [!WARNING]
> **ESTADO DEL PROYECTO: VERSIÓN BETA**  
> Este repositorio se encuentra actualmente en fase BETA. La integración es funcional, pero aún puede contener errores, comportamientos inesperados o cambios estructurales menores.  
> No se recomienda su uso en entornos críticos o de producción hasta el lanzamiento de la primera versión estable.

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

### 🚧 Incidencias de Tráfico (BETA temprana)

- Accidentes
- Retenciones
- Obras
- Eventos especiales

⚠️ Este módulo aún está en desarrollo activo y puede presentar resultados incompletos o inconsistentes.

---

### ⚡ Electrolineras (BETA funcional)

- Filtrado por radio configurable
- Coordenadas automáticas o personalizadas
- Sensores agregados (totales, cercanas, potencia, etc.)
- Entidades dinámicas por estación
- Clasificación por rangos de potencia
- Visualización directa en mapa

Este módulo se considera funcional para uso en pruebas.

---

## ✨ Características principales

- 📍 Geolocalización automática o manual (lat/lon)
- 📏 Cálculo real de distancia mediante `geopy`
- 🧭 Filtrado por radio configurable
- 🔌 Parsing completo DATEX2 de electrolineras
- 🗺️ Soporte para visualización directa en mapa
- 📊 Sensores agregados + entidades individuales por estación
- 🧠 Coordinadores y arquitectura limpia orientada a escalabilidad

---

## 🛠️ Instalación

Actualmente no existe versión oficial en HACS.

Instalación manual:

1. Copiar la carpeta `dgt_traffic` `dentro de: config/custom_components/``

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

---

## 🧪 Estado actual

- **Electrolineras**: funcional (BETA)  
- **Incidencias**: en desarrollo activo  
- **Frontend**: se proporciona como ejemplo  

---

## 🐞 Reporte de errores

A partir de esta versión BETA ya se aceptan Issues.

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


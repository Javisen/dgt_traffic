# 🚦 DGT Traffic (Pro) para Home Assistant

> [!WARNING]
> **ESTADO DEL PROYECTO: VERSIÓN ALFA** > Este repositorio se encuentra actualmente en fase de desarrollo intensivo (WIP). El código no es estable, puede contener errores críticos y está sujeto a cambios estructurales profundos sin previo aviso. **No se recomienda su instalación en entornos de producción hasta el lanzamiento de la primera versión estable.**

## 💡 Sobre el Proyecto
**DGT Traffic** es una integración avanzada y propietaria diseñada para Home Assistant que permite la monitorización en tiempo real de incidencias de tráfico, obras, eventos y alertas meteorológicas proporcionadas por la **Dirección General de Tráfico (DGT)** de España.

Este proyecto nace para llenar un vacío en la comunidad española de domótica, ofreciendo un control granular basado en geolocalización que hasta ahora no existía con este nivel de detalle.

## ✨ Características en Desarrollo
* 📍 **Geofencing Inteligente**: Filtrado por municipio, provincia y radio de acción (km).
* ⚠️ **Gestión de Incidencias**: Sensores específicos para Accidentes, Retenciones, Obras y Meteorología.
* 📏 **Cálculo de Proximidad**: Identificación de la distancia exacta a la incidencia más cercana mediante `geopy`.
* 📋 **Atributos Técnicos**: Información detallada del punto kilométrico, sentido de la marcha y descripción de la restricción.

## 🛠️ Instalación (Solo para desarrolladores/curiosos)
Actualmente no existe una versión en HACS. La instalación manual bajo su propio riesgo se realiza copiando la carpeta `dgt_traffic` en `custom_components`. 

**Nota:** Requiere las dependencias `geopy` y `xmltodict`.

## ⚖️ Derechos Reservados y Licencia
Este software es obra original de **Javisen**. 

* **Copyright (c) 2026 Javisen**
* Distribuido bajo la **Licencia MIT**.

Aunque la licencia permite el uso del código, se hace constar que la **idea original, la estructura de filtrado geográfico y la implementación técnica** son propiedad intelectual del autor. Se agradece a los curiosos y desarrolladores que visiten el repo que respeten la autoría y esperen a las versiones oficiales para realizar forks o sugerencias.

---
**¿Has encontrado un error?** Por favor, no abras incidencias (Issues) todavía. El código está siendo depurado diariamente.

*Desarrollado con ❤️ en España para la comunidad de Home Assistant.*

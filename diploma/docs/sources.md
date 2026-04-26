# Список использованных источников

> **Правила добавления:**
> - Источники нумеруются **в порядке упоминания** в тексте, не по алфавиту.
> - Формат — ГОСТ 7.1-2003 (см. `style-guide.md`, раздел 2).
> - Каждый новый источник добавляется в конец, со следующим номером.
> - В тексте — `[N]`, `[N, с. M]`, `[N—M]`.
>
> **Заполняемость:** этот файл начинается со скелета по категориям. Конкретные библиографические записи дописываются по мере того, как агент пишет соответствующие секции.

---

## Стандарты (всегда нужны для оформления, добавляются в первую очередь)

```
1. ГОСТ 7.32-2017. Система стандартов по информации, библиотечному и издательскому делу.
   Отчёт о научно-исследовательской работе. Структура и правила оформления. – М. :
   Стандартинформ, 2017. – 32 с.

2. ГОСТ 7.1-2003. Система стандартов по информации, библиотечному и издательскому делу.
   Библиографическая запись. Библиографическое описание. Общие требования и правила
   составления. – М. : ИПК Изд-во стандартов, 2004. – 48 с.

3. ГОСТ Р 7.0.5-2008. Система стандартов по информации, библиотечному и издательскому делу.
   Библиографическая ссылка. Общие требования и правила составления. – М. :
   Стандартинформ, 2008. – 23 с.
```

---

## Категории-заглушки (заполнить по мере написания глав)

> Ниже — структура какие источники нужны для какой главы. Конкретные записи добавляются в общий список выше при упоминании в тексте. После сборки минимум 20 источников.

### Глава 2 — Аналитический обзор методов 3D-реконструкции

- [ ] Обзорная статья по методам реконструкции 3D из 2D (например, Han et al., 2019 — "Image-based 3D Object Reconstruction: State-of-the-Art and Trends").
- [ ] Mildenhall, B. NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis [Электронный ресурс] / B. Mildenhall, P.P. Srinivasan, M. Tancik, [et al.]. – arXiv preprint arXiv:2003.08934, 2020.
- [ ] Diffusion-based 3D — DreamFusion (Poole et al., 2022) или Magic3D (Lin et al., 2022).
- [ ] **TripoSR**: Tochilkin, D. TripoSR: Fast 3D Object Reconstruction from a Single Image [Электронный ресурс] / D. Tochilkin, [et al.]. – arXiv preprint arXiv:2403.02151, 2024.
- [ ] LRM / Triplane методы как фундамент TripoSR (Hong et al., 2023 — Large Reconstruction Model).
- [ ] **ShapeNet**: Chang, A.X. ShapeNet: An Information-Rich 3D Model Repository [Электронный ресурс] / A.X. Chang, [et al.]. – arXiv preprint arXiv:1512.03012, 2015.

### Глава 3 — Анализ требований к системе

- [ ] Bass, L. Software Architecture in Practice / L. Bass, P. Clements, R. Kazman. – 4th ed. – Boston : Addison-Wesley, 2021. (требования и архитектурные качества: производительность, доступность, масштабируемость).
- [ ] ISO/IEC 25010:2011 — модель качества ПО (атрибуты системы).

### Глава 4 — Проектирование микросервисной архитектуры

- [ ] **Newman**, S. Building Microservices: Designing Fine-Grained Systems / S. Newman. – 2nd ed. – Sebastopol : O'Reilly Media, 2021. – 612 p.
- [ ] **Richardson**, C. Microservices Patterns: With Examples in Java / C. Richardson. – Shelter Island : Manning, 2018. – 520 p.
- [ ] Fowler, M. Microservices [Электронный ресурс] / M. Fowler, J. Lewis. – 2014. – URL : https://martinfowler.com/articles/microservices.html
- [ ] **Kleppmann**, M. Designing Data-Intensive Applications / M. Kleppmann. – Sebastopol : O'Reilly Media, 2017. – 590 p. (про Kafka, event-driven, репликация).
- [ ] gRPC vs REST бенчмарк — академическая статья (например, Indrasiri et al., 2018, или Polyakov et al., 2022).
- [ ] Apache Kafka документация / книга (Narkhede et al., "Kafka: The Definitive Guide").

### Глава 5 — Программная реализация

- [ ] Spring Boot Reference Documentation [Электронный ресурс]. – VMware Tanzu, 2024. – URL : https://docs.spring.io/spring-boot
- [ ] FastAPI Documentation [Электронный ресурс] / S. Ramírez. – URL : https://fastapi.tiangolo.com/
- [ ] Docker Documentation [Электронный ресурс]. – Docker Inc. – URL : https://docs.docker.com/
- [ ] PostgreSQL Documentation, MinIO Documentation (по необходимости).

### Глава 6 — Дообучение TripoSR

- [ ] Howard, J. Universal Language Model Fine-tuning for Text Classification (или аналог по transfer learning) — для обоснования fine-tune подхода.
- [ ] Tatarchenko, M. What Do Single-view 3D Reconstruction Networks Learn? / M. Tatarchenko, [et al.] // CVPR. – 2019. (про метрики Chamfer и оценку 3D-реконструкции).
- [ ] Knapitsch, A. Tanks and Temples: Benchmarking Large-Scale Scene Reconstruction / A. Knapitsch, [et al.] // ACM TOG. – 2017. (метрика F-score для 3D).
- [ ] Статья по fine-tune моделей 3D-реконструкции с показанным улучшением метрик (для ссылки на ожидаемые +5%).

### Глава 7 — Эксперименты

- [ ] Molyneaux, I. The Art of Application Performance Testing / I. Molyneaux. – 2nd ed. – Sebastopol : O'Reilly Media, 2014.
- [ ] k6 Load Testing Documentation [Электронный ресурс] / Grafana Labs. – URL : https://k6.io/docs/
- [ ] (опционально) Gatling Documentation, JMeter — если используются.

### Препроцессинг (если в главе 5 будет описан)

- [ ] Qin, X. U2-Net: Going Deeper with Nested U-Structure for Salient Object Detection / X. Qin, [et al.] // Pattern Recognition. – 2020. – Vol. 106. – Article 107404.
- [ ] RemBG (или аналог) — GitHub-репозиторий.

---

## Целевое количество

**Минимум 20** источников в финальной версии (рекомендация по бакалаврской ВКР).
**Цель:** 22–28 — даёт безопасный запас на случай если какие-то источники придётся убрать.

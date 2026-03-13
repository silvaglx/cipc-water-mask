# Water Body Extraction Prototype for WFI Sensors
## Gabriel Lucas Xavier da Silva — Bolsista DTI-B

---

## 1. Project Context and Scope

This project aims to build a **Python-based prototype** for automated water body detection (water mask) from Wide Field Imager (WFI) sensor images of three Brazilian satellites: CBERS-4, CBERS-4A, and Amazonia-1. The core methodology adapts Namikawa et al. (2016) — which uses RGB→HSV color transformation and Minimum Normalized Radiance (MNR) thresholding — originally developed for 5-band, 5 m RapidEye imagery, to the 4-band, 55–64 m WFI context. Sentinel-2 data is leveraged for validation, complementary masking (clouds, shadows), and algorithm enhancement.

### 1.1 WFI Sensor Summary

| Parameter | CBERS-4 WFI | CBERS-4A WFI | Amazonia-1 WFI |
|-----------|------------|-------------|----------------|
| Spatial Resolution | 64 m | 55 m | 64 m |
| Swath Width | 866 km | 684 km | 850 km |
| Temporal Resolution | 5 days | 5 days | 5 days |
| Bands | Blue, Green, Red, NIR | Blue, Green, Red, NIR | Blue, Green, Red, NIR |
| Blue (µm) | 0.45–0.52 | 0.45–0.52 | 0.45–0.52 |
| Green (µm) | 0.52–0.59 | 0.52–0.59 | 0.52–0.59 |
| Red (µm) | 0.63–0.69 | 0.63–0.69 | 0.63–0.69 |
| NIR (µm) | 0.77–0.89 | 0.77–0.89 | 0.77–0.89 |
| Orbit Altitude | 778 km | 628 km | 752 km |
| Data Format | GeoTIFF (L4 ortho) | GeoTIFF (L4 ortho) | GeoTIFF (L4 ortho) |

**Key difference from RapidEye:** WFI has 4 bands (no RedEdge), versus RapidEye's 5 bands. However, the best band composition found in Namikawa et al. (2016) — R2G3B5 (Green, Red, NIR) — uses only bands that exist in WFI, making the method directly transferable.

### 1.2 Mapping of RapidEye Method to WFI

| Namikawa (2016) | RapidEye Bands Used | WFI Equivalent |
|-----------------|-------------------|----------------|
| R channel (for HSV) | Band 2 – Green | Band 2 – Green |
| G channel (for HSV) | Band 3 – Red | Band 3 – Red |
| B channel (for HSV) | Band 5 – NIR | Band 4 – NIR |
| MNR (min of all bands) | min(B1..B5) | min(B1..B4) |

---

## 2. Methodological Workflow

### Phase 0: Environment Setup and Data Infrastructure (Months 1–2)

**Objective:** Set up the Python development environment, establish data access pipelines, and create the project skeleton.

#### 2.0.1 Python Environment and Package Structure

```
watermask/
├── pyproject.toml
├── README.md
├── src/
│   └── watermask/
│       ├── __init__.py
│       ├── io/                  # Data I/O and catalog access
│       │   ├── __init__.py
│       │   ├── stac_client.py   # STAC API wrappers (INPE, AWS, BDC)
│       │   ├── download.py      # Band download utilities
│       │   └── readers.py       # GeoTIFF/COG readers
│       ├── preprocessing/       # Radiometric/geometric preprocessing
│       │   ├── __init__.py
│       │   ├── toa_reflectance.py  # DN → TOA reflectance conversion
│       │   ├── harmonization.py    # Cross-sensor harmonization
│       │   └── sunglint.py         # Sunglint detection and masking
│       ├── masks/               # Ancillary mask generation
│       │   ├── __init__.py
│       │   ├── cloud_shadow.py  # Cloud/shadow masks
│       │   ├── hand_mask.py     # HAND-based terrain filtering
│       │   └── vegetation.py    # Vegetation on water detection
│       ├── core/                # Core water detection algorithm
│       │   ├── __init__.py
│       │   ├── hsv_transform.py # RGB → HSV conversion
│       │   ├── hue_classify.py  # Hue-based water classification
│       │   ├── mnr_filter.py    # Minimum Normalized Radiance filter
│       │   └── water_mask.py    # Pipeline orchestrator
│       ├── validation/          # Accuracy assessment
│       │   ├── __init__.py
│       │   ├── sentinel2_ref.py # Sentinel-2 reference data
│       │   └── metrics.py       # Accuracy metrics
│       └── products/            # Derived products
│           ├── __init__.py
│           ├── occurrence.py    # Water occurrence maps
│           ├── seasonality.py   # Seasonality analysis
│           └── export.py        # GeoTIFF/COG export
├── notebooks/                   # Jupyter notebooks for exploration
├── tests/                       # Unit and integration tests
├── configs/                     # YAML config files per satellite
│   ├── cbers4_wfi.yaml
│   ├── cbers4a_wfi.yaml
│   └── amazonia1_wfi.yaml
└── data/                        # Local data cache (gitignored)
```

**Core dependencies:** `rasterio`, `numpy`, `scipy`, `xarray`, `dask`, `geopandas`, `shapely`, `pystac-client`, `matplotlib`, `scikit-image`, `pyproj`, `pyyaml`.

#### 2.0.2 Data Access Setup

Three complementary data access routes:

1. **INPE STAC API** (`https://data.inpe.br/stac/browser/?.language=en`): Official INPE catalog, includes WFI L4 products from all three satellites in GeoTIFF format.
2. **CBERS on AWS** (`https://registry.opendata.aws/cbers/`): Cloud-optimized GeoTIFF (COG) format, ideal for direct streaming without full download.
3. **cbers4asat Python library** (`pip install cbers4asat`): Convenience wrapper for searching and downloading CBERS-4A and Amazonia-1 imagery from the INPE DGI catalog.

**Practical step:** Create a configuration-driven STAC client that abstracts the catalog endpoint, collection ID, and band naming differences across all three satellites. Store per-satellite metadata (band names, calibration coefficients, solar exoatmospheric irradiance values) in YAML configs.

#### 2.0.3 Ancillary Data Acquisition

| Data | Source | Resolution | Purpose |
|------|--------|-----------|---------|
| HAND | Copernicus GLO-30 HAND (AWS `glo-30-hand` bucket) | 30 m | Terrain-based water probability filter |
| Copernicus DEM (COP-30) | AWS or Copernicus Data Space | 30 m | HAND generation (if custom thresholds needed) |
| Sentinel-2 L2A | Copernicus Data Space / Element84 Earth Search | 10–20 m | Validation, Fmask, SWIR-based water indices |
| JRC Global Surface Water | Google Earth Engine / direct download | 30 m | Validation reference and derived product comparison |

---

### Phase 1: Study and Baseline Implementation (Months 1–4)

**Objective:** Implement the Namikawa (2016) algorithm in Python and establish baseline performance on WFI images.

#### Step 1.1 — Literature Review (Month 1)

Deep study of:
- Namikawa et al. (2016): RGB→HSV methodology, Hue thresholding, MNR filtering, 7-class confidence system.
- Traditional water indices: NDWI (McFeeters, 1996), MNDWI (Xu, 2006).
- Pekel et al. (2016, Nature): JRC Global Surface Water methodology — Expert System classifier, multi-temporal compositing, occurrence/seasonality/transitions framework.
- HAND terrain model: Nobre et al. (2011, J. Hydrology) — hydrologically relevant terrain normalization.
- Sunglint: Kay et al. (2009, Remote Sensing) — comprehensive review of glint correction methods.
- WFI calibration: Pinto et al. (2016) — CBERS-4 WFI/MUX in-flight radiometric calibration.

#### Step 1.2 — Technical Study of WFI Products (Months 1–2)

**Practical actions:**
1. Download sample WFI images from each satellite (CBERS-4, CBERS-4A, Amazonia-1) for at least 2 contrasting study areas (e.g., one reservoir-dominated area like Jacareí/SP, one Amazonian area with rivers and floodplains).
2. Inspect product metadata: DN range, bit depth (typically 8-bit for WFI L4), coordinate system (UTM), band ordering.
3. Compute and compare TOA reflectance spectra for water, vegetation, urban, shadow, and bare soil targets across the three satellites to characterize inter-sensor differences.
4. Document the DN → radiance → TOA reflectance conversion pipeline for each satellite, using published calibration coefficients and solar exoatmospheric irradiance values (ESUNλ).

**DN to TOA Reflectance formula:**
```
ρ_TOA = (π × L_λ × d²) / (ESUN_λ × cos(θ_s))
```
where `L_λ = gain × DN + offset`, `d` = Earth-Sun distance, `θ_s` = solar zenith angle.

#### Step 1.3 — Baseline Algorithm Implementation (Months 2–4)

Implement the Namikawa (2016) method as a Python module:

**Step 1.3.1 — RGB→HSV Transformation:**
- Input: 3 WFI bands assigned as R=Green, G=Red, B=NIR (best composition from the paper).
- Normalize bands to [0, 1] using TOA reflectance.
- Apply the standard Foley et al. (1996) RGB→HSV algorithm:
  ```python
  def rgb_to_hsv(r, g, b):
      """Vectorized RGB to HSV following Foley et al. (1996)."""
      cmax = np.maximum(np.maximum(r, g), b)
      cmin = np.minimum(np.minimum(r, g), b)
      delta = cmax - cmin
      
      # Hue calculation (0–360°)
      h = np.where(delta == 0, 0,
          np.where(cmax == r, 60 * (((g - b) / delta) % 6),
          np.where(cmax == g, 60 * (((b - r) / delta) + 2),
                               60 * (((r - g) / delta) + 4))))
      
      # Saturation
      s = np.where(cmax == 0, 0, delta / cmax)
      
      # Value
      v = cmax
      return h, s, v
  ```

**Step 1.3.2 — Hue Thresholding:**
- Apply Namikawa's R2G3B5 thresholds (Table 4 from paper):
  - WATER: Hue 16°–35°
  - WATER95: Hue 35°–36° and 324°–16°
  - WATER90: Hue 36°–37° and 308°–324°
  - WATER80: Hue 37°–160° (with MNR filter)
- **Critical validation step:** These thresholds were derived from RapidEye. WFI has different spectral response functions (SRFs). The thresholds must be recalibrated for WFI using reference water/non-water samples from K-Means classification (same procedure as the paper).

**Step 1.3.3 — Minimum Normalized Radiance (MNR) Filter:**
- For each pixel, compute the minimum of normalized reflectance across all 4 WFI bands.
- Apply percentile-based thresholds (from the paper: 90%, 95%, 99%, 99.5% cumulative distribution) to discriminate water classes WATER80 through WATER50.
- This step is crucial for reducing commission errors from high-reflectance urban features.

**Step 1.3.4 — Combined Classification:**
- Combine Hue classes + MNR filter → 7 confidence classes.
- Output as a single-band GeoTIFF with class values 1–7 (WATER to WATER50).

**Validation:** Compare the baseline output against K-Means unsupervised classification and NDWI for the same study areas. Compute confusion matrices (omission/commission errors).

---

### Phase 2: Algorithm Enhancement with Auxiliary Variables (Months 3–8)

**Objective:** Improve the baseline algorithm by incorporating ancillary data sources that address known limitations.

#### Step 2.1 — HAND Integration (Months 3–5)

**Rationale:** HAND (Height Above Nearest Drainage) provides a terrain-based prior probability for water occurrence. Pixels at low HAND values (close to drainage network) have higher probability of being water; pixels at high HAND values are very unlikely to be water bodies.

**Implementation:**
1. Download GLO-30 HAND tiles from AWS (`s3://glo-30-hand/`) covering the study area.
2. Resample HAND to WFI resolution (55–64 m) using bilinear interpolation.
3. Use HAND as a post-classification filter:
   - HAND < 5 m: High probability zone — accept all water classes.
   - HAND 5–15 m: Medium probability — accept only WATER, WATER95, WATER90.
   - HAND > 15 m: Low probability — flag as likely false positive (shadows, dark urban) unless confirmed by multiple indicators.
4. Alternatively, use HAND as a continuous weight in a probabilistic framework.

**Expected impact:** Significant reduction in commission errors from shadows and dark urban areas in upland regions.

#### Step 2.2 — Cloud and Shadow Masking (Months 3–5)

**Rationale:** Cloud shadows have spectral signatures very similar to water, causing major commission errors. Clouds themselves obscure water bodies.

**Implementation options:**
1. **Sentinel-2 Fmask (SCL band):** When Sentinel-2 L2A imagery is available (near-temporally to WFI), use the Scene Classification Layer (SCL) which provides cloud, cloud shadow, water, vegetation, and other classes at 20 m resolution. Resample and project to WFI grid.
2. **Custom shadow detection for WFI:** Since WFI lacks SWIR bands (critical for Fmask), develop a shadow detection approach using:
   - NIR band darkness (water-like but contextually different).
   - Solar geometry (sun azimuth/elevation) + DEM-derived shadow casting.
   - Temporal consistency: shadows move between acquisitions; water doesn't (unless ephemeral).
3. **Cloud detection for WFI:** Use brightness thresholds in visible bands + spatial texture analysis (clouds are bright and have smooth texture).

#### Step 2.3 — Sunglint Detection and Correction (Months 4–6)

**Rationale:** Sunglint is the specular reflection of sunlight from water surfaces toward the sensor. It makes water appear bright (sometimes brighter than land), directly countering the low-reflectance assumption underlying all water detection methods.

**Implementation:**
1. **Glint angle calculation:** Using sun and sensor geometry from image metadata:
   ```python
   def glint_angle(solar_azimuth, solar_zenith, view_azimuth, view_zenith):
       """Calculate the specular reflection angle between sun and sensor."""
       cos_glint = (np.cos(solar_zenith) * np.cos(view_zenith) +
                    np.sin(solar_zenith) * np.sin(view_zenith) *
                    np.cos(solar_azimuth - view_azimuth))
       return np.degrees(np.arccos(np.clip(cos_glint, -1, 1)))
   ```
2. **Masking approach:** Pixels with glint angle < 20–25° are flagged as potentially sunglint-affected.
3. **Correction approach (for less severe cases):** NIR-based deglinting following Hedley et al. (2005) — regress visible bands against NIR over deep water to estimate and subtract glint contribution.
4. **WFI-specific considerations:** The wide swath of WFI (684–866 km) means significant variation in viewing geometry across the scene, and sunglint patterns can affect large portions of the image.

#### Step 2.4 — Vegetation on Water Surface (Months 5–7)

**Rationale:** Aquatic macrophytes, floating vegetation, and algal blooms modify water reflectance, increasing NIR and reducing the spectral contrast that the HSV method relies on.

**Implementation:**
1. Compute NDVI within detected water bodies: high NDVI (> 0.2) within water regions indicates vegetation.
2. Flag these pixels as "vegetated water" — a separate class that extends the water mask rather than excluding it.
3. Use Sentinel-2 RedEdge bands (when available) for more precise discrimination of chlorophyll-rich water vs. emergent vegetation.

---

### Phase 3: TOA Reflectance Harmonization (Months 4–7)

**Objective:** Ensure that the same physical target produces consistent reflectance values across all three WFI sensors, enabling a single set of classification thresholds.

**Rationale:** Despite similar spectral band definitions, the three WFI sensors have different Spectral Response Functions (SRFs), calibration histories, and orbital characteristics. Without harmonization, water detection thresholds optimized for one sensor will not transfer cleanly to others.

**Approach:**

1. **Cross-calibration using Pseudo-Invariant Calibration Sites (PICS):** Use sites like the Libya-4 desert site or the Algodones Dunes (used for CBERS-4 calibration in Pinto et al., 2016) to compare TOA reflectance between sensors for the same ground target.

2. **Sentinel-2 as reference:** Use Sentinel-2 L2A surface reflectance as a harmonization target. For near-simultaneous overpasses:
   - Resample Sentinel-2 to WFI resolution.
   - Compute band-by-band regression (slope + offset) for each WFI sensor relative to Sentinel-2.
   - Apply correction factors to normalize WFI reflectance.

3. **Spectral Band Adjustment Factor (SBAF):** Account for differences in SRFs by computing SBAFs using a reference spectral library (e.g., USGS spectral library) convolved with each sensor's SRF.

4. **Implementation:**
   ```python
   # Per-satellite harmonization config
   harmonization:
     reference: "sentinel2_l2a"
     cbers4_wfi:
       blue: {slope: 1.02, offset: -0.001}
       green: {slope: 0.98, offset: 0.003}
       red: {slope: 1.01, offset: -0.002}
       nir: {slope: 0.97, offset: 0.005}
     cbers4a_wfi:
       blue: {slope: 1.00, offset: 0.001}
       ...
   ```

---

### Phase 4: Sentinel-2 Comparative Analysis (Months 5–9)

**Objective:** Use Sentinel-2 data to validate, improve, and complement the WFI water mask.

#### 4.1 Sentinel-2 as Validation Reference

- Sentinel-2 MSI has 10 m visible bands and 20 m SWIR bands → much higher spatial detail.
- Compute MNDWI = (Green - SWIR1) / (Green + SWIR1) using Sentinel-2 bands 3 and 11.
- Generate high-confidence water masks from Sentinel-2 MNDWI (threshold > 0) + SCL water class.
- Resample to WFI resolution → use as reference for accuracy assessment.

#### 4.2 Sentinel-2 as Complementary Input

- For operational scenarios where Sentinel-2 is available (near-temporal to WFI):
  - Use Sentinel-2 SWIR-based water mask to augment WFI detection in challenging areas (turbid water, sunglint).
  - Use Sentinel-2 cloud/shadow mask (SCL) to filter WFI results.
- Explore simple fusion: WFI provides frequent coverage (combined 5-day from 3 satellites), Sentinel-2 provides spectral depth → temporal + spectral synergy.

#### 4.3 Accuracy Metrics

For each study area, compute:
- Overall Accuracy, Kappa coefficient.
- Producer's Accuracy (1 - omission error) and User's Accuracy (1 - commission error) for the water class.
- F1-score for water detection.
- Compare against NDWI, MNDWI, and JRC Global Surface Water products.

---

### Phase 5: Prototype Development and Integration (Months 7–16)

**Objective:** Consolidate all modules into a production-ready prototype.

#### 5.1 Processing Pipeline

The prototype should implement a configurable pipeline:

```
Input: WFI scene (any satellite) + config file
  │
  ├─ 1. Read scene metadata and bands
  ├─ 2. DN → TOA reflectance conversion (per-satellite coefficients)
  ├─ 3. Cross-sensor harmonization (optional, for multi-satellite consistency)
  ├─ 4. Sunglint detection and masking/correction
  ├─ 5. RGB→HSV transformation (Green, Red, NIR as R, G, B)
  ├─ 6. Hue-based water classification (7 confidence classes)
  ├─ 7. MNR filter refinement
  ├─ 8. Cloud/shadow mask application
  ├─ 9. HAND-based terrain filtering
  ├─ 10. Vegetation-on-water flagging
  ├─ 11. Contextual reclassification (noise removal, edge refinement)
  │
  Output: Water mask GeoTIFF (7 classes + NoData + Cloud + Shadow + Sunglint flags)
```

#### 5.2 Configuration-Driven Design

Use YAML config files per satellite:

```yaml
# cbers4_wfi.yaml
satellite: "CBERS-4"
sensor: "WFI"
spatial_resolution: 64
bands:
  blue: {index: 1, wavelength: [0.45, 0.52], esun: 1984.65}
  green: {index: 2, wavelength: [0.52, 0.59], esun: 1823.40}
  red: {index: 3, wavelength: [0.63, 0.69], esun: 1559.20}
  nir: {index: 4, wavelength: [0.77, 0.89], esun: 1076.30}
calibration:
  gain: [0.379, 0.498, 0.360, 0.351]  # from Pinto et al., 2016
  offset: [0, 0, 0, 0]
hsv:
  r_band: "green"
  g_band: "red"
  b_band: "nir"
thresholds:  # To be calibrated during Phase 1
  water: {hue_min: 16, hue_max: 35}
  water95: {hue_ranges: [[35, 36], [324, 16]]}
  # ... (remaining classes)
mnr:
  percentiles: {p90: null, p95: null, p99: null, p995: null}  # To be derived
hand:
  threshold_high_prob: 5
  threshold_med_prob: 15
sunglint:
  glint_angle_threshold: 25
```

#### 5.3 Batch Processing

For operational use across Brazil:
- Implement `dask` or `multiprocessing`-based parallelization.
- Process WFI tiles independently (embarrassingly parallel).
- Use COG format for cloud-native processing without full download.

---

### Phase 6: Derived Products (Months 14–20)

**Objective:** Generate products analogous to JRC Global Surface Water, using the WFI water mask time series.

#### 6.1 Product Definitions (inspired by JRC GSW)

| Product | Definition | Computation |
|---------|-----------|-------------|
| Water Occurrence | % of valid observations where water was detected | `count(water) / count(valid)` per pixel |
| Occurrence Change | Difference in occurrence between two epochs | `occurrence(epoch2) - occurrence(epoch1)` |
| Seasonality | Number of months with water in a given year | Monthly aggregation of water detections |
| Recurrence | Frequency of seasonal water presence across years | Inter-annual consistency metric |
| Transitions | Change between permanent, seasonal, and absent water | State-transition classification |
| Maximum Water Extent | Union of all water detections | Binary OR across all temporal observations |

#### 6.2 Implementation

- Leverage the Brazil Data Cube (BDC) infrastructure for temporal compositing.
- Output as COG-format GeoTIFFs with embedded color maps.
- Integration with OGC web services (WMS/WMTS) for visualization.

---

## 3. Timeline Alignment with Cronogram

| Cronogram Activity | Plan Phase | Months |
|-------------------|-----------|--------|
| Revisão bibliográfica | Phase 1, Step 1.1 | 1–2 |
| Estudo técnico WFI | Phase 0 + Phase 1, Step 1.2 | 1–3 |
| Exercícios RGB→HSV | Phase 1, Step 1.3 | 2–4 |
| Testes com HAND, sombras, vegetação, sunglint | Phase 2 (all steps) | 3–8 |
| Análise comparativa Sentinel-2 | Phase 4 | 5–9 |
| Desenvolvimento do protótipo | Phase 5 | 7–16 |
| Aprimoramento e implementação | Phase 5 (refinement) | 13–20 |
| Produtos derivados | Phase 6 | 14–20 |

---

## 4. Practical First Steps (Month 1 Checklist)

### Week 1: Environment
- [x] Set up Python 3.11+ environment with conda/venv.
- [x] Install core dependencies: `rasterio`, `numpy`, `xarray`, `pystac-client`, `shapely`, `geopandas`, `matplotlib`, `scikit-image`.
- [x] Initialize git repository with the package structure above.
- [x] Create YAML config templates for each satellite.

### Week 2: Data Access
- [ ] Register at INPE DGI catalog (https://www.dgi.inpe.br/catalogo/explore).
- [ ] Test `cbers4asat` library: search and download a WFI scene from each satellite.
- [ ] Test STAC API access via `pystac-client` to INPE and AWS endpoints.
- [ ] Download HAND tiles for study areas from AWS.
- [ ] Download sample Sentinel-2 L2A scenes (near-temporal to WFI) from Copernicus Data Space.

### Week 3: Data Exploration
- [ ] Load WFI bands with `rasterio`, inspect metadata (CRS, resolution, DN range, solar angles).
- [ ] Compute TOA reflectance for all bands of one scene per satellite.
- [ ] Plot spectral profiles for water, vegetation, urban, shadow, bare soil targets.
- [ ] Compare reflectance values across the three satellites for similar targets.

### Week 4: Baseline Algorithm
- [ ] Implement `rgb_to_hsv()` function (vectorized with NumPy).
- [ ] Compute Hue images for WFI using Green-Red-NIR composition.
- [ ] Visualize Hue histograms for water vs. non-water (using manually digitized samples or K-Means).
- [ ] Compare Namikawa's RapidEye thresholds with WFI Hue distributions.
- [ ] Document discrepancies and plan threshold recalibration.

---

## 5. Key Technical Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Hue thresholds from RapidEye don't transfer to WFI | Algorithm fails on WFI | Recalibrate thresholds empirically using WFI training samples (same methodology as paper) |
| WFI coarse resolution (55–64 m) misses small water bodies | Omission errors for small rivers/ponds | Accept resolution limitation; use HAND to infer likely water in narrow channels |
| No SWIR band on WFI | Cannot compute MNDWI; harder to separate water from shadows | Rely on HSV+MNR method; use HAND and temporal consistency; leverage Sentinel-2 SWIR when available |
| Sunglint across wide WFI swath | Large areas of false negatives (water looks bright) | Implement glint angle masking + NIR deglinting; flag severely affected scenes |
| Inconsistent calibration across 3 satellites | Threshold instability | Harmonize to Sentinel-2 reference; maintain per-satellite correction factors |
| Cloud contamination in Amazon (frequent cloud cover) | Reduced usable imagery | Combine 3 satellites for near-daily revisit; temporal compositing to fill gaps |

---

## 6. Tools and References Summary

### Python Libraries
- **Geospatial I/O:** `rasterio`, `xarray`, `rioxarray`, `geopandas`, `fiona`
- **STAC/Data access:** `pystac-client`, `cbers4asat`, `stackstac`
- **Image processing:** `scikit-image`, `scipy.ndimage`, `opencv-python`
- **Parallelism:** `dask`, `dask-geopandas`, `joblib`
- **Visualization:** `matplotlib`, `folium`, `contextily`
- **Machine learning (optional):** `scikit-learn` (for K-Means, Random Forest refinement)

### Key References
1. Namikawa, L. M.; Körting, T.; Castejon, E. F. (2016). Water Body Extraction From RapidEye Images. RBC, v. 68, p. 1097-1111.
2. Pekel, J.-F. et al. (2016). High-resolution mapping of global surface water and its long-term changes. Nature, 540, 418-422.
3. McFeeters, S. K. (1996). The use of NDWI in the delineation of open water features. Int. J. Remote Sensing, 17(7), 1425-1432.
4. Xu, H. (2006). Modification of NDWI to enhance open water features. Int. J. Remote Sensing, 27(14), 3025-3033.
5. Nobre, A. D. et al. (2011). HAND — a hydrologically relevant new terrain model. J. Hydrology, 404, 13-29.
6. Kay, S. et al. (2009). Sun Glint Correction — a review. Remote Sensing, 1(4), 697-730.
7. Pinto, C. T. et al. (2016). First in-flight radiometric calibration of MUX and WFI on-board CBERS-4. Remote Sensing, 8(5), 405.

### Data Sources
- INPE STAC: `https://data.inpe.br/stac/browser/?.language=en`
- CBERS/Amazonia-1 on AWS: `https://registry.opendata.aws/cbers/`
- GLO-30 HAND on AWS: `s3://glo-30-hand/`
- Sentinel-2 L2A on AWS: Element84 Earth Search STAC (`https://earth-search.aws.element84.com/v1/`)
- JRC Global Surface Water: `https://global-surface-water.appspot.com/`
- Brazil Data Cube: `https://data.inpe.br/bdc/`

---

*Document prepared as initial project planning reference.*
*To be revised and updated as the project progresses.*

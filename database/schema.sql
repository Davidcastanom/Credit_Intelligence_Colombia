-- ============================================
-- CREDIT INTELLIGENCE COLOMBIA
-- Esquema de Base de Datos - 8 Tablas
-- ============================================

PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS sync_logs;
DROP TABLE IF EXISTS tasas;
DROP TABLE IF EXISTS historico_tasas;
DROP TABLE IF EXISTS indicadores;
DROP TABLE IF EXISTS productos;
DROP TABLE IF EXISTS fuentes;
DROP TABLE IF EXISTS categorias_credito;
DROP TABLE IF EXISTS bancos;

DROP TABLE IF EXISTS productos_financieros;
DROP TABLE IF EXISTS usura_modalidades;
DROP TABLE IF EXISTS tasas_historico;

PRAGMA foreign_keys = ON;

-- Índices para rendimiento y unicidad
-- Los indices se crean despues de las tablas.

-- 1. Bancos
CREATE TABLE bancos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nit TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    razon_social TEXT,
    url_web TEXT,
    tipo_entidad TEXT NOT NULL DEFAULT 'Banco tradicional'
);

-- 2. Categorias de Credito
CREATE TABLE categorias_credito (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    descripcion TEXT,
    modalidad_usura TEXT NOT NULL
);

-- 3. Fuentes
CREATE TABLE fuentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    tipo TEXT NOT NULL, -- 'API', 'Scraper', 'Manual', 'OpenData', 'Oficial'
    url TEXT
);

-- 4. Productos Financieros
CREATE TABLE productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    banco_id INTEGER NOT NULL,
    categoria_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    FOREIGN KEY (banco_id) REFERENCES bancos(id) ON DELETE CASCADE,
    FOREIGN KEY (categoria_id) REFERENCES categorias_credito(id) ON DELETE CASCADE
);

-- 5. Tasas Vigentes
CREATE TABLE tasas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER UNIQUE NOT NULL,
    tasa_ea REAL NOT NULL,
    tasa_mv REAL NOT NULL,
    fuente_id INTEGER NOT NULL,
    fecha_actualizacion TEXT NOT NULL,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
    FOREIGN KEY (fuente_id) REFERENCES fuentes(id) ON DELETE CASCADE
);

-- 6. Historial de Tasas
CREATE TABLE historico_tasas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    tasa_ea REAL NOT NULL,
    tasa_mv REAL NOT NULL,
    fecha_registro TEXT NOT NULL,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

-- 7. Indicadores de Mercado
CREATE TABLE indicadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    valor REAL NOT NULL,
    fecha_vigencia_inicio TEXT NOT NULL,
    fecha_vigencia_fin TEXT NOT NULL
);

-- 8. Historial de Indicadores (Usura, DTF, etc.)
CREATE TABLE historico_indicadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    valor REAL NOT NULL,
    fuente_id INTEGER NOT NULL,
    fecha_consulta TEXT NOT NULL,
    fecha_vigencia_inicio TEXT NOT NULL,
    fecha_vigencia_fin TEXT NOT NULL,
    FOREIGN KEY (fuente_id) REFERENCES fuentes(id) ON DELETE CASCADE
);

-- 9. Logs de Sincronizacion ETL
CREATE TABLE sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_ejecucion TEXT NOT NULL,
    fuente_id INTEGER NOT NULL,
    estado TEXT NOT NULL,
    registros_procesados INTEGER NOT NULL,
    detalles TEXT,
    FOREIGN KEY (fuente_id) REFERENCES fuentes(id) ON DELETE CASCADE
);

-- Indices para rendimiento y unicidad
CREATE UNIQUE INDEX IF NOT EXISTS idx_historico_tasas_unique ON historico_tasas(producto_id, fecha_registro);
CREATE UNIQUE INDEX IF NOT EXISTS idx_historico_indicadores_unique ON historico_indicadores(nombre, fecha_vigencia_inicio, fecha_consulta);
CREATE INDEX IF NOT EXISTS idx_sync_logs_fecha ON sync_logs(fecha_ejecucion);
CREATE INDEX IF NOT EXISTS idx_historico_tasas_fecha ON historico_tasas(fecha_registro);
CREATE INDEX IF NOT EXISTS idx_historico_indicadores_nombre ON historico_indicadores(nombre);

-- ============================================
-- DATOS SEMILLA (COLOMBIA)
-- ============================================

-- Bancos y entidades financieras clasificadas
INSERT INTO bancos (id, nit, nombre, razon_social, url_web, tipo_entidad) VALUES
(1, '890903938-8', 'Bancolombia', 'BANCOLOMBIA S.A.', 'https://www.bancolombia.com', 'Banco tradicional'),
(2, '860002964-4', 'Banco de Bogota', 'BANCO DE BOGOTA S.A.', 'https://www.bancodebogota.com', 'Banco tradicional'),
(3, '901587541-9', 'Nequi', 'NEQUI S.A. COMPANIA DE FINANCIAMIENTO', 'https://www.nequi.com.co', 'Nubanco'),
(4, '890981395-1', 'Confiar', 'CONFIAR COOPERATIVA FINANCIERA', 'https://www.confiar.coop', 'Cooperativa'),
(5, '860034313-7', 'Banco Davivienda', 'BANCO DAVIVIENDA S.A.', 'https://www.davivienda.com', 'Banco tradicional'),
(6, '860003020-1', 'BBVA Colombia', 'BANCO BILBAO VIZCAYA ARGENTARIA COLOMBIA S.A.', 'https://www.bbva.com.co', 'Banco tradicional'),
(7, '860007738-9', 'Banco Popular', 'BANCO POPULAR S.A.', 'https://www.bancopopular.com.co', 'Banco tradicional'),
(8, '890300279-4', 'Banco de Occidente', 'BANCO DE OCCIDENTE S.A.', 'https://www.bancodeoccidente.com.co', 'Banco tradicional'),
(9, '860035827-5', 'Banco AV Villas', 'BANCO COMERCIAL AV VILLAS S.A.', 'https://www.avvillas.com.co', 'Banco tradicional'),
(10, '860007335-4', 'Banco Caja Social', 'BANCO CAJA SOCIAL S.A.', 'https://www.bancocajasocial.com', 'Banco tradicional'),
(11, '860034594-1', 'Scotiabank Colpatria', 'SCOTIABANK COLPATRIA S.A.', 'https://www.scotiabankcolpatria.com', 'Banco tradicional'),
(12, '800037800-8', 'Banco Agrario', 'BANCO AGRARIO DE COLOMBIA S.A.', 'https://www.bancoagrario.gov.co', 'Banco tradicional'),
(13, '890903937-0', 'Itau Colombia', 'ITAU COLOMBIA S.A.', 'https://www.itau.co', 'Banco tradicional'),
(14, '900047981-8', 'Banco Falabella', 'BANCO FALABELLA S.A.', 'https://www.bancofalabella.com.co', 'Banco tradicional'),
(15, '890200756-7', 'Banco Pichincha', 'BANCO PICHINCHA S.A.', 'https://www.bancopichincha.com.co', 'Banco tradicional'),
(16, '901659846-8', 'Nu Colombia', 'NU COLOMBIA COMPANIA DE FINANCIAMIENTO S.A.', 'https://nu.com.co', 'Nubanco'),
(17, '901353491-1', 'Lulo Bank', 'LULO BANK S.A.', 'https://www.lulobank.com', 'Nubanco'),
(18, '901400002-9', 'RappiPay', 'RAPPIPAY COMPANIA DE FINANCIAMIENTO S.A.', 'https://www.rappipay.co', 'Nubanco'),
(19, '901097473-5', 'Uala Colombia', 'UALA COLOMBIA S.A.', 'https://www.uala.com.co', 'Nubanco'),
(20, '890906213-1', 'Coofinep', 'COOFINEP COOPERATIVA FINANCIERA', 'https://www.coofinep.com', 'Cooperativa'),
(21, '890901176-3', 'Cotrafa', 'COTRAFA COOPERATIVA FINANCIERA', 'https://www.cotrafa.com.co', 'Cooperativa'),
(22, '890907489-5', 'JFK Cooperativa Financiera', 'JFK COOPERATIVA FINANCIERA', 'https://www.jfk.com.co', 'Cooperativa'),
(23, '890985032-6', 'Fincomercio', 'COOPERATIVA DE AHORRO Y CREDITO FINCOMERCIO', 'https://www.fincomercio.com', 'Cooperativa');

-- Categorias de Credito
INSERT INTO categorias_credito (id, nombre, descripcion, modalidad_usura) VALUES
(1, 'Consumo', 'Creditos orientados a libre inversion, compra de bienes o servicios.', 'tasa_usura_consumo_ordinario'),
(2, 'Bajo Monto', 'Creditos de consumo de bajo monto con limites especiales.', 'tasa_usura_bajo_monto'),
(3, 'Vivienda', 'Creditos de vivienda para adquisicion o leasing habitacional.', 'tasa_usura_consumo_ordinario'),
(4, 'Microcredito', 'Financiacion de actividades productivas de microempresas.', 'tasa_usura_productivo_urbano'),
(5, 'Libranza', 'Creditos de consumo descontados por nomina o pension.', 'tasa_usura_consumo_ordinario'),
(6, 'Vehiculo', 'Financiacion para compra de vehiculo nuevo o usado.', 'tasa_usura_consumo_ordinario'),
(7, 'Comercial', 'Creditos para capital de trabajo, inversion empresarial o actividad productiva.', 'tasa_usura_consumo_ordinario'),
(8, 'Productivo Mayor Monto', 'Creditos productivos de mayor monto certificados por modalidad SFC.', 'tasa_usura_productivo_mayor_monto'),
(9, 'Productivo Rural', 'Creditos productivos rurales certificados por modalidad SFC.', 'tasa_usura_productivo_rural'),
(10, 'Productivo Urbano', 'Creditos productivos urbanos certificados por modalidad SFC.', 'tasa_usura_productivo_urbano'),
(11, 'Popular Productivo Rural', 'Creditos populares productivos rurales certificados por modalidad SFC.', 'tasa_usura_popular_productivo_rural'),
(12, 'Popular Productivo Urbano', 'Creditos populares productivos urbanos certificados por modalidad SFC.', 'tasa_usura_popular_productivo_urbano');

-- Fuentes oficiales por entidad o regulador
INSERT INTO fuentes (id, nombre, tipo, url) VALUES
(1, 'Superfinanciera Seguimiento TIBC', 'Oficial', 'https://www.superfinanciera.gov.co/publicaciones/10115837/seguimiento-a-la-tibc/'),
(2, 'Bancolombia Oficial', 'Oficial', 'https://www.bancolombia.com/personas/creditos'),
(3, 'Banco de Bogota Oficial', 'Oficial', 'https://www.bancodebogota.com/personas/creditos'),
(4, 'Nequi Oficial', 'Oficial', 'https://www.nequi.com.co'),
(5, 'Confiar Oficial', 'Oficial', 'https://www.confiar.coop/personas/creditos'),
(6, 'Davivienda Oficial', 'Oficial', 'https://www.davivienda.com/wps/portal/personas/nuevo/personas/aqui_puedo/'),
(7, 'BBVA Colombia Oficial', 'Oficial', 'https://www.bbva.com.co/personas/productos/prestamos.html'),
(8, 'Banco Popular Oficial', 'Oficial', 'https://www.bancopopular.com.co/wps/portal/bancopopular/inicio/para-ti/creditos'),
(9, 'Banco de Occidente Oficial', 'Oficial', 'https://www.bancodeoccidente.com.co/wps/portal/banco-de-occidente/bancodeoccidente/para-personas/creditos/'),
(10, 'Banco AV Villas Oficial', 'Oficial', 'https://www.avvillas.com.co/wps/portal/avvillas/banco/personas/productos/creditos/'),
(11, 'Banco Caja Social Oficial', 'Oficial', 'https://www.bancocajasocial.com/personas/creditos'),
(12, 'Scotiabank Colpatria Oficial', 'Oficial', 'https://www.scotiabankcolpatria.com/personas/prestamos'),
(13, 'Banco Agrario Oficial', 'Oficial', 'https://www.bancoagrario.gov.co/personas/credito'),
(14, 'Itau Colombia Oficial', 'Oficial', 'https://www.itau.co/personas/creditos'),
(15, 'Banco Falabella Oficial', 'Oficial', 'https://www.bancofalabella.com.co/creditos'),
(16, 'Banco Pichincha Oficial', 'Oficial', 'https://www.bancopichincha.com.co/web/personas/creditos'),
(17, 'Nu Colombia Oficial', 'Oficial', 'https://nu.com.co/prestamo/'),
(18, 'Lulo Bank Oficial', 'Oficial', 'https://www.lulobank.com'),
(19, 'RappiPay Oficial', 'Oficial', 'https://www.rappipay.co'),
(20, 'Uala Colombia Oficial', 'Oficial', 'https://www.uala.com.co'),
(21, 'Coofinep Oficial', 'Oficial', 'https://www.coofinep.com/personas/creditos'),
(22, 'Cotrafa Oficial', 'Oficial', 'https://www.cotrafa.com.co/creditos'),
(23, 'JFK Cooperativa Oficial', 'Oficial', 'https://www.jfk.com.co/creditos'),
(24, 'Fincomercio Oficial', 'Oficial', 'https://www.fincomercio.com/creditos');

-- Productos Financieros
INSERT INTO productos (id, banco_id, categoria_id, nombre, descripcion) VALUES
(1, 1, 1, 'Libre Inversion Bancolombia', 'Credito de libre destinacion con tasa fija.'),
(2, 1, 3, 'Hipotecario Pesos Bancolombia', 'Credito hipotecario tradicional.'),
(3, 2, 1, 'Libre Destinacion Banco de Bogota', 'Credito de libre inversion Banco de Bogota.'),
(4, 3, 2, 'Prestamo Propio Nequi', 'Credito digital de bajo monto en Nequi.'),
(5, 4, 4, 'Microcredito Confiar', 'Credito productivo para microempresarios Confiar.'),
(6, 5, 1, 'Credito Movil Davivienda', 'Credito de consumo digital rotativo.'),
(7, 6, 1, 'Prestamo de Libre Inversion BBVA', 'Credito de consumo de libre destino.'),
(8, 7, 5, 'Credito de Libranza Banco Popular', 'Credito de libranza para empleados y pensionados.'),
(9, 8, 6, 'Credito de Vehiculo Banco de Occidente', 'Financiacion de vehiculo nuevo o usado.'),
(10, 9, 1, 'Credito Libre Inversion AV Villas', 'Credito de consumo de libre inversion.'),
(11, 10, 1, 'Credito Libre Inversion Banco Caja Social', 'Credito de consumo para personas.'),
(12, 11, 3, 'Credito Hipotecario Scotiabank Colpatria', 'Financiacion de vivienda en pesos.'),
(13, 12, 4, 'Microcredito Banco Agrario', 'Credito productivo rural y urbano.'),
(14, 13, 1, 'Credito Libre Inversion Itau', 'Prestamo de libre destino para personas.'),
(15, 14, 1, 'Credito de Libre Inversion Banco Falabella', 'Credito de consumo para clientes Banco Falabella.'),
(16, 15, 7, 'Credito Comercial Banco Pichincha', 'Financiacion para actividad productiva o empresarial.'),
(17, 16, 2, 'Prestamo Nu Colombia', 'Credito digital de bajo monto.'),
(18, 17, 1, 'Credito Digital Lulo Bank', 'Credito de consumo solicitado por canales digitales.'),
(19, 18, 2, 'Credito RappiPay', 'Credito digital de bajo monto.'),
(20, 19, 1, 'Credito Digital Uala', 'Credito de consumo digital.'),
(21, 20, 4, 'Microcredito Coofinep', 'Credito productivo para independientes y microempresas.'),
(22, 21, 1, 'Credito de Consumo Cotrafa', 'Credito de consumo para asociados.'),
(23, 22, 5, 'Libranza JFK Cooperativa', 'Credito de libranza para asociados.'),
(24, 23, 1, 'Credito de Consumo Fincomercio', 'Credito de consumo para asociados.');

-- Tasas Vigentes (EA y MV calculada con: (1 + EA/100)^(1/12) - 1)
INSERT INTO tasas (producto_id, tasa_ea, tasa_mv, fuente_id, fecha_actualizacion) VALUES
(1, 24.50, 1.84, 2, '2026-06-29'),
(2, 14.20, 1.11, 2, '2026-06-29'),
(3, 25.80, 1.93, 3, '2026-06-29'),
(4, 27.80, 2.07, 4, '2026-06-29'),
(5, 38.00, 2.72, 5, '2026-06-29'),
(6, 26.20, 1.96, 6, '2026-06-29'),
(7, 23.90, 1.80, 7, '2026-06-29'),
(8, 24.80, 1.86, 8, '2026-06-29'),
(9, 25.10, 1.88, 9, '2026-06-29'),
(10, 24.30, 1.83, 10, '2026-06-29'),
(11, 22.90, 1.73, 11, '2026-06-29'),
(12, 18.70, 1.44, 12, '2026-06-29'),
(13, 24.70, 1.86, 13, '2026-06-29'),
(14, 26.60, 1.98, 14, '2026-06-29'),
(15, 25.40, 1.90, 15, '2026-06-29'),
(16, 29.20, 2.16, 16, '2026-06-29'),
(17, 27.10, 2.02, 17, '2026-06-29'),
(18, 28.40, 2.11, 18, '2026-06-29'),
(19, 23.50, 1.77, 19, '2026-06-29'),
(20, 26.90, 2.00, 20, '2026-06-29'),
(21, 36.80, 2.65, 21, '2026-06-29'),
(22, 37.20, 2.67, 22, '2026-06-29'),
(23, 35.90, 2.59, 23, '2026-06-29'),
(24, 34.70, 2.51, 24, '2026-06-29');

-- Historial de Tasas (ultimas 4 semanas para tendencias)
INSERT INTO historico_tasas (producto_id, tasa_ea, tasa_mv, fecha_registro) VALUES
(1, 25.10, 1.88, '2026-06-08'), (1, 24.80, 1.86, '2026-06-15'), (1, 24.50, 1.84, '2026-06-22'), (1, 24.50, 1.84, '2026-06-29'),
(4, 28.20, 2.09, '2026-06-08'), (4, 28.00, 2.08, '2026-06-15'), (4, 27.80, 2.07, '2026-06-22'), (4, 27.80, 2.07, '2026-06-29'),
(5, 39.50, 2.80, '2026-06-08'), (5, 38.90, 2.77, '2026-06-15'), (5, 38.00, 2.72, '2026-06-22'), (5, 38.00, 2.72, '2026-06-29'),
(6, 26.90, 2.00, '2026-06-08'), (6, 26.50, 1.97, '2026-06-15'), (6, 26.20, 1.96, '2026-06-22'), (6, 26.20, 1.96, '2026-06-29'),
(7, 24.70, 1.86, '2026-06-08'), (7, 24.40, 1.84, '2026-06-15'), (7, 24.10, 1.81, '2026-06-22'), (7, 23.90, 1.80, '2026-06-29'),
(11, 23.60, 1.78, '2026-06-08'), (11, 23.30, 1.76, '2026-06-15'), (11, 23.10, 1.74, '2026-06-22'), (11, 22.90, 1.73, '2026-06-29'),
(17, 27.90, 2.07, '2026-06-08'), (17, 27.60, 2.05, '2026-06-15'), (17, 27.30, 2.03, '2026-06-22'), (17, 27.10, 2.02, '2026-06-29'),
(19, 24.20, 1.82, '2026-06-08'), (19, 23.90, 1.80, '2026-06-15'), (19, 23.70, 1.78, '2026-06-22'), (19, 23.50, 1.77, '2026-06-29'),
(21, 37.90, 2.72, '2026-06-08'), (21, 37.50, 2.69, '2026-06-15'), (21, 37.10, 2.67, '2026-06-22'), (21, 36.80, 2.65, '2026-06-29'),
(24, 35.80, 2.58, '2026-06-08'), (24, 35.40, 2.55, '2026-06-15'), (24, 35.00, 2.53, '2026-06-22'), (24, 34.70, 2.51, '2026-06-29');

-- Indicadores de Mercado
INSERT INTO indicadores (nombre, valor, fecha_vigencia_inicio, fecha_vigencia_fin) VALUES
('tasa_usura_consumo_ordinario', 28.79, '2026-06-01', '2026-06-30'),
('tasa_usura_bajo_monto', 62.10, '2026-06-01', '2026-06-30'),
('tasa_usura_productivo_mayor_monto', 42.50, '2026-06-01', '2026-06-30'),
('tasa_usura_productivo_rural', 42.50, '2026-06-01', '2026-06-30'),
('tasa_usura_productivo_urbano', 42.50, '2026-06-01', '2026-06-30'),
('tasa_usura_popular_productivo_rural', 62.10, '2026-06-01', '2026-06-30'),
('tasa_usura_popular_productivo_urbano', 62.10, '2026-06-01', '2026-06-30'),
('tasa_usura_consumo', 28.79, '2026-06-01', '2026-06-30'),
('tasa_usura_microcredito', 42.50, '2026-06-01', '2026-06-30'),
('dtf_ea', 10.50, '2026-06-25', '2026-07-02');

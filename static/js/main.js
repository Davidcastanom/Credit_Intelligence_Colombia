// URL base de la API
const API_URL = "";

// Formateador de moneda colombiana
const formatCOP = (num) => {
    return new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'COP',
        minimumFractionDigits: 0
    }).format(num);
};

// Utilidad: descargar CSV compatible con Excel (locale es-CO)
function descargarCSV(datos, columnas, nombreArchivo) {
    if (!datos || datos.length === 0) return;
    const SEP = ";";
    const DEC = ",";
    const cabecera = columnas.map(c => c.titulo).join(SEP);
    const filas = datos.map(fila =>
        columnas.map(c => {
            let val = fila[c.campo];
            if (typeof val === "number") {
                return String(val).replace(".", DEC);
            }
            if (typeof val === "string") {
                if (val.includes(SEP) || val.includes('"')) {
                    return `"${val.replace(/"/g, '""')}"`;
                }
                return val;
            }
            return val != null ? String(val) : "";
        }).join(SEP)
    );
    const csv = "\uFEFF" + cabecera + "\n" + filas.join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    const ext = ".csv";
    link.download = nombreArchivo.replace(/[^a-zA-Z0-9_\u00f1\u00d1]/g, "_") + ext;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
}

// ============================================
// LÓGICA DEL COMPARADOR DE TASAS
// ============================================
let tasasDatos = [];
let usuraConsumo = 28.79;
let indicadoresUsura = {
    tasa_usura_consumo_ordinario: 28.79,
    tasa_usura_bajo_monto: 62.10,
    tasa_usura_productivo_mayor_monto: 42.50,
    tasa_usura_productivo_rural: 42.50,
    tasa_usura_productivo_urbano: 42.50,
    tasa_usura_popular_productivo_rural: 62.10,
    tasa_usura_popular_productivo_urbano: 62.10,
    tasa_usura_consumo: 28.79,
    tasa_usura_microcredito: 42.50
};

async function inicializarComparador() {
    try {
        // Cargar indicadores de usura primero
        const resInd = await fetch(`${API_URL}/api/indicadores`);
        const indicadores = await resInd.json();
        const usuraObj = indicadores.find(i => i.nombre === 'tasa_usura_consumo');
        if (usuraObj) usuraConsumo = usuraObj.valor;
        actualizarIndicadoresUsura(indicadores);

        // Cargar tasas
        const response = await fetch(`${API_URL}/api/tasas`);
        tasasDatos = await response.json();
        
        // Configurar escuchadores de filtros
        document.getElementById('buscar').addEventListener('input', filtrarYMostrarTasas);
        document.getElementById('filtro-categoria').addEventListener('change', filtrarYMostrarTasas);
        document.getElementById('filtro-tipo-entidad').addEventListener('change', filtrarYMostrarTasas);
        document.getElementById('orden-tasa').addEventListener('change', filtrarYMostrarTasas);

        filtrarYMostrarTasas();
    } catch (error) {
        console.error("Error al cargar comparador:", error);
    }
}

function filtrarYMostrarTasas() {
    const buscarTexto = document.getElementById('buscar').value.toLowerCase();
    const categoriaFiltro = document.getElementById('filtro-categoria').value;
    const tipoEntidadFiltro = document.getElementById('filtro-tipo-entidad').value;
    const ordenTasa = document.getElementById('orden-tasa').value;

    let datosFiltrados = tasasDatos.filter(fila => {
        const coincideBusqueda = fila.banco.toLowerCase().includes(buscarTexto) || 
                                fila.producto.toLowerCase().includes(buscarTexto);
        const coincideCategoria = (categoriaFiltro === "todas") || (fila.categoria === categoriaFiltro);
        const coincideTipoEntidad = (tipoEntidadFiltro === "todas") || (fila.tipo_entidad === tipoEntidadFiltro);
        return coincideBusqueda && coincideCategoria && coincideTipoEntidad;
    });

    // Ordenar por tasa
    datosFiltrados.sort((a, b) => {
        return ordenTasa === "asc" ? a.tasa_ea - b.tasa_ea : b.tasa_ea - a.tasa_ea;
    });

    const tbody = document.getElementById('tabla-body');
    tbody.innerHTML = "";

    datosFiltrados.forEach(fila => {
        // Calcular nivel de riesgo respecto al indicador aplicable al tipo de credito
        const usuraAplicable = obtenerUsuraPorCategoria(fila);
        const distancia = usuraAplicable - fila.tasa_ea;
        let badgeClase = "badge-success";
        let badgeTexto = "Bajo Riesgo";

        if (distancia <= 1.0) {
            badgeClase = "badge-danger";
            badgeTexto = "Límite Usura";
        } else if (distancia <= 3.0) {
            badgeClase = "badge-warning";
            badgeTexto = "Riesgo Medio";
        }

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="font-weight: 600;">${fila.banco}</td>
            <td><span class="badge badge-info">${fila.tipo_entidad}</span></td>
            <td>${fila.producto}</td>
            <td>${fila.categoria}</td>
            <td style="font-weight: 700; color: #60a5fa;">${fila.tasa_ea.toFixed(2)}%</td>
            <td>${fila.tasa_mv.toFixed(2)}%</td>
            <td><span class="badge ${badgeClase}">${badgeTexto}</span></td>
            <td>${fila.fecha_actualizacion}</td>
            <td><a href="${fila.url_fuente}" target="_blank" class="link-fuente">${fila.fuente}</a></td>
        `;
        tbody.appendChild(tr);
    });
}

function actualizarIndicadoresUsura(indicadores) {
    indicadores.forEach(indicador => {
        if (indicador.nombre.startsWith('tasa_usura_')) {
            indicadoresUsura[indicador.nombre] = indicador.valor;
        }
    });

    usuraConsumo = indicadoresUsura.tasa_usura_consumo_ordinario ||
        indicadoresUsura.tasa_usura_consumo ||
        usuraConsumo;
}

function obtenerUsuraPorCategoria(fila) {
    return indicadoresUsura[fila.modalidad_usura] || usuraConsumo;
}

// ============================================
// LÓGICA DE LA CALCULADORA FRANCESA
// ============================================
let ultimaTablaAmortizacion = [];
let usuraPorModalidad = {};
let modalidadSeleccionada = 'tasa_usura_consumo';

function exportarAmortizacion() {
    if (ultimaTablaAmortizacion.length === 0) return;
    const monto = document.getElementById('monto').value;
    const tasa = document.getElementById('tasa_ea').value;
    const plazo = document.getElementById('plazo').value;
    const columnas = [
        { campo: "mes", titulo: "Mes" },
        { campo: "cuota", titulo: "Cuota Fija" },
        { campo: "interes", titulo: "Intereses" },
        { campo: "capital", titulo: "Abono Capital" },
        { campo: "saldo", titulo: "Saldo Pendiente" }
    ];
    descargarCSV(ultimaTablaAmortizacion, columnas,
        `amortizacion_${monto}_${tasa}_${plazo}meses`);
}

async function inicializarCalculadora() {
    // Configurar sliders y sus inputs
    conectarSliderEInput('monto', 'monto-slider');
    conectarSliderEInput('tasa_ea', 'tasa-slider');
    conectarSliderEInput('plazo', 'plazo-slider');

    // Cargar indicadores de usura vigentes
    try {
        const resInd = await fetch(`${API_URL}/api/indicadores`);
        const indicadores = await resInd.json();
        actualizarIndicadoresUsura(indicadores);
        indicadores.forEach(i => { usuraPorModalidad[i.nombre] = i.valor; });
        usuraConsumo = usuraPorModalidad['tasa_usura_consumo_ordinario'] ||
            usuraPorModalidad['tasa_usura_consumo'] || 28.79;
        const alertaPanel = document.getElementById('usura-alerta');
        if (alertaPanel) {
            alertaPanel.className = "info-banner success";
            alertaPanel.innerHTML = `🛡️ <strong>Tasa de Usura Vigente:</strong> Consumo ordinario está en <strong>${usuraConsumo}% E.A.</strong>`;
        }
    } catch (e) {
        console.error("Error al cargar usura:", e);
    }

    // Cargar tasas de bancos en el dropdown con modalidad
    try {
        const response = await fetch(`${API_URL}/api/tasas`);
        const tasas = await response.json();
        const select = document.getElementById('select-banco-tasa');

        tasas.forEach(t => {
            const option = document.createElement('option');
            option.value = t.tasa_ea;
            option.dataset.modalidad = t.modalidad_usura || 'tasa_usura_consumo';
            option.textContent = `${t.banco} - ${t.producto} (${t.tasa_ea}%)`;
            select.appendChild(option);
        });

        select.addEventListener('change', (e) => {
            const opt = e.target.selectedOptions[0];
            if (opt && opt.value) {
                document.getElementById('tasa_ea').value = opt.value;
                document.getElementById('tasa-slider').value = opt.value;
                modalidadSeleccionada = opt.dataset.modalidad || 'tasa_usura_consumo';
                ejecutarSimulacion();
            }
        });
    } catch (e) {
        console.error("Error cargando selector de tasas:", e);
    }

    document.getElementById('btn-calcular').addEventListener('click', ejecutarSimulacion);
    
    // Ejecutar simulación inicial
    ejecutarSimulacion();
}

function conectarSliderEInput(inputId, sliderId) {
    const input = document.getElementById(inputId);
    const slider = document.getElementById(sliderId);

    input.addEventListener('input', () => {
        const val = parseFloat(input.value);
        const min = parseFloat(slider.min);
        const max = parseFloat(slider.max);
        if (!isNaN(val) && val >= min && val <= max) {
            slider.value = val;
        }
    });

    slider.addEventListener('input', () => {
        input.value = slider.value;
    });

    input.addEventListener('blur', () => {
        const val = parseFloat(input.value);
        const min = parseFloat(slider.min);
        const max = parseFloat(slider.max);
        if (!isNaN(val)) {
            if (val < min) input.value = min;
            if (val > max) input.value = max;
            slider.value = input.value;
        }
    });
}

async function ejecutarSimulacion() {
    const monto = parseFloat(document.getElementById('monto').value);
    const tasa_ea = parseFloat(document.getElementById('tasa_ea').value);
    const plazo = parseInt(document.getElementById('plazo').value);

    if (isNaN(monto) || isNaN(tasa_ea) || isNaN(plazo) || monto <= 0 || tasa_ea <= 0 || plazo <= 0) {
        alert("Ingrese valores numéricos válidos mayores a cero.");
        return;
    }

    // Usura por modalidad de crédito
    const usuraAplicable = usuraPorModalidad[modalidadSeleccionada]
        || usuraPorModalidad['tasa_usura_consumo_ordinario']
        || usuraPorModalidad['tasa_usura_consumo']
        || usuraConsumo;
    const alertaPanel = document.getElementById('usura-alerta');
    const diferencia = usuraAplicable - tasa_ea;
    const modalidadNombre = modalidadSeleccionada
        .replace('tasa_usura_', '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

    if (tasa_ea > usuraAplicable) {
        alertaPanel.className = "info-banner danger";
        alertaPanel.innerHTML = `⚠ <strong>¡ALERTA DE USURA!</strong> La tasa ingresada (<strong>${tasa_ea}% E.A.</strong>) excede el límite legal de <strong>${modalidadNombre} (${usuraAplicable}% E.A.)</strong>`;
    } else if (diferencia <= 2.0) {
        alertaPanel.className = "info-banner warning";
        alertaPanel.innerHTML = `⚠ <strong>USURA PREVENTIVA:</strong> La tasa ingresada (<strong>${tasa_ea}% E.A.</strong>) está a solo <strong>${diferencia.toFixed(2)}%</strong> del límite de <strong>${modalidadNombre} (${usuraAplicable}% E.A.)</strong>`;
    } else {
        alertaPanel.className = "info-banner success";
        alertaPanel.innerHTML = `Tasa dentro del margen normal. Está a <strong>${diferencia.toFixed(2)}%</strong> del límite de <strong>${modalidadNombre} (${usuraAplicable}% E.A.)</strong>`;
    }

    try {
        const response = await fetch(`${API_URL}/api/amortizacion?monto=${monto}&tasa_ea=${tasa_ea}&plazo=${plazo}`);
        const data = await response.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        // Mostrar totales
        document.getElementById('res-cuota').textContent = formatCOP(data.cuota_mensual);
        document.getElementById('res-tasa-mv').textContent = `${data.tasa_mv}%`;
        document.getElementById('res-total-interes').textContent = formatCOP(data.total_interes || (data.cuota_mensual * plazo - monto));

        // Guardar para exportacion
        ultimaTablaAmortizacion = data.tabla;

        // Llenar tabla
        const tbody = document.getElementById('amortizacion-body');
        tbody.innerHTML = "";

        data.tabla.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight: 600;">${row.mes}</td>
                <td style="font-weight: 700; color: var(--color-primary);">${formatCOP(row.cuota)}</td>
                <td style="color: var(--color-danger);">${formatCOP(row.interes)}</td>
                <td style="color: var(--color-success);">${formatCOP(row.capital)}</td>
                <td style="font-weight: 500; color: var(--color-text-muted);">${formatCOP(row.saldo)}</td>
            `;
            tbody.appendChild(tr);
        });

    } catch (error) {
        console.error("Error al calcular cuota:", error);
    }
}

// ============================================
// LÓGICA DEL DASHBOARD DE ESTADÍSTICAS
// ============================================

const COLORES_BANCOS = [
    '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
    '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16',
    '#e11d48', '#0ea5e9', '#a855f7', '#22c55e', '#eab308',
    '#06b6d4', '#d946ef', '#64748b', '#fb923c', '#38bdf8',
    '#a3e635', '#c084fc', '#34d399', '#f472b6'
];

let tasasDatosDashboard = [];
let historialDatosDashboard = [];
let historialUsuraDashboard = [];
let indicadoresUsuraDashboard = {};
let chartBarInstance = null;
let chartLineInstance = null;
let chartUsuraInstance = null;

async function inicializarDashboard() {
    try {
        const [tasas, indicadores, historial, histUsura, syncStatus] = await Promise.all([
            fetch(`${API_URL}/api/tasas`).then(r => r.json()),
            fetch(`${API_URL}/api/indicadores`).then(r => r.json()),
            fetch(`${API_URL}/api/historial`).then(r => r.json()),
            fetch(`${API_URL}/api/historial/usura`).then(r => r.json()),
            fetch(`${API_URL}/api/sync/status`).then(r => r.json()),
        ]);

        tasasDatosDashboard = tasas;
        historialDatosDashboard = historial;
        historialUsuraDashboard = histUsura;
        actualizarIndicadoresUsura(indicadores);

        const indicadoresNorm = {};
        indicadores.forEach(i => { indicadoresNorm[i.nombre] = i.valor; });
        indicadoresUsuraDashboard = indicadoresNorm;

        renderizarKPIs(tasas, indicadoresNorm);
        renderizarSyncStatus(syncStatus);
        renderizarAlertas(tasas, indicadoresNorm);
        llenarSelectBancos(tasas);

        // Configurar filtros
        document.getElementById('filtro-categoria-dash').addEventListener('change', aplicarFiltrosDashboard);
        document.getElementById('filtro-banco-dash').addEventListener('change', aplicarFiltrosDashboard);
        document.getElementById('filtro-entidad-dash').addEventListener('change', aplicarFiltrosDashboard);

        document.querySelectorAll('#filtro-rango .pill').forEach(pill => {
            pill.addEventListener('click', function() {
                document.querySelectorAll('#filtro-rango .pill').forEach(p => p.classList.remove('active'));
                this.classList.add('active');
                aplicarFiltrosDashboard();
            });
        });

        aplicarFiltrosDashboard();

        // Usura history chart (no depende de filtros de fecha)
        renderizarUsuraChart(histUsura);

    } catch (e) {
        console.error("Error cargando dashboard:", e);
    }
}

function renderizarKPIs(tasas, indicadores) {
    const usuraCons = indicadores['tasa_usura_consumo'] || indicadores['tasa_usura_consumo_ordinario'] || 28.79;
    document.getElementById('dash-usura').textContent = `${usuraCons.toFixed(2)}%`;
    document.getElementById('dash-usura-modalidad').textContent = `Consumo Ordinario`;

    const tasasConsumo = tasas.filter(t => t.categoria === 'Consumo');
    if (tasasConsumo.length > 0) {
        tasasConsumo.sort((a, b) => a.tasa_ea - b.tasa_ea);
        const mejor = tasasConsumo[0];
        document.getElementById('dash-mejor-tasa').textContent = `${mejor.tasa_ea.toFixed(2)}%`;
        document.getElementById('dash-mejor-banco').textContent = `${mejor.banco} (${mejor.producto})`;

        const suma = tasasConsumo.reduce((acc, curr) => acc + curr.tasa_ea, 0);
        const prom = suma / tasasConsumo.length;
        document.getElementById('dash-promedio').textContent = `${prom.toFixed(2)}%`;
    }

    const alertas = obtenerAlertas(tasas, indicadores);
    document.getElementById('dash-alertas').textContent = alertas.length;
    document.getElementById('dash-alertas').style.color = alertas.length > 0 ? 'var(--color-error)' : 'var(--color-success)';
    document.getElementById('dash-alertas-desc').textContent = alertas.length === 1
        ? 'producto cerca del l\u00edmite'
        : 'productos cerca del l\u00edmite';
}

function obtenerAlertas(tasas, indicadores) {
    const alertas = [];
    tasas.forEach(t => {
        const usuraAplicable = indicadores[t.modalidad_usura]
            || indicadores['tasa_usura_consumo']
            || indicadores['tasa_usura_consumo_ordinario']
            || 28.79;
        const distancia = usuraAplicable - t.tasa_ea;
        if (distancia <= 3.0) {
            alertas.push({ ...t, distancia, usuraAplicable });
        }
    });
    alertas.sort((a, b) => a.distancia - b.distancia);
    return alertas;
}

function renderizarAlertas(tasas, indicadores) {
    const alertas = obtenerAlertas(tasas, indicadores);
    const container = document.getElementById('alertas-body');
    const panel = document.getElementById('alertas-panel');
    const tableContainer = document.getElementById('alertas-table-container');
    const emptyMsg = document.getElementById('alertas-empty');
    const countBadge = document.getElementById('alertas-count');

    if (!panel) return;

    countBadge.textContent = `${alertas.length} producto(s) en riesgo`;

    if (alertas.length === 0) {
        tableContainer.style.display = 'none';
        emptyMsg.style.display = 'block';
        return;
    }

    tableContainer.style.display = 'block';
    emptyMsg.style.display = 'none';
    container.innerHTML = '';

    alertas.forEach(a => {
        let gravedad, badgeClase, icono;
        if (a.distancia <= 1.0) {
            gravedad = 'Cr\u00edtica';
            badgeClase = 'badge-danger';
            icono = '\ud83d\udd34';
        } else {
            gravedad = 'Preventiva';
            badgeClase = 'badge-warning';
            icono = '\ud83d\udfe1';
        }

        const tr = document.createElement('tr');
        tr.className = a.distancia <= 1.0 ? 'alerta-critica' : 'alerta-preventiva';
        tr.innerHTML = `
            <td><span class="badge ${badgeClase}">${icono} ${gravedad}</span></td>
            <td style="font-weight:600;">${a.banco}</td>
            <td>${a.producto}</td>
            <td>${a.categoria}</td>
            <td style="font-weight:700;">${a.tasa_ea.toFixed(2)}%</td>
            <td>${a.usuraAplicable.toFixed(2)}%</td>
            <td style="font-weight:600; color: ${a.distancia <= 1.0 ? 'var(--color-error)' : 'var(--color-warning)'};">${a.distancia.toFixed(2)}%</td>
        `;
        container.appendChild(tr);
    });
}

function llenarSelectBancos(tasas) {
    const select = document.getElementById('filtro-banco-dash');
    const bancos = [...new Set(tasas.map(t => t.banco))].sort();
    bancos.forEach(b => {
        const opt = document.createElement('option');
        opt.value = b;
        opt.textContent = b;
        select.appendChild(opt);
    });
}

function obtenerColorBanco(banco, index) {
    if (!window._bancoColorMap) {
        window._bancoColorMap = {};
    }
    if (!window._bancoColorMap[banco]) {
        window._bancoColorMap[banco] = COLORES_BANCOS[index % COLORES_BANCOS.length];
    }
    return window._bancoColorMap[banco];
}

function aplicarFiltrosDashboard() {
    const categoriaFiltro = document.getElementById('filtro-categoria-dash').value;
    const bancoFiltro = document.getElementById('filtro-banco-dash').value;
    const entidadFiltro = document.getElementById('filtro-entidad-dash').value;

    const pillActive = document.querySelector('#filtro-rango .pill.active');
    const rangoDias = pillActive ? pillActive.dataset.value : 'all';

    // Filtrar tasas para bar chart
    let tasasFiltradas = tasasDatosDashboard.filter(t => {
        const coincideCategoria = (categoriaFiltro === 'todas') || (t.categoria === categoriaFiltro);
        const coincideEntidad = (entidadFiltro === 'todas') || (t.tipo_entidad === entidadFiltro);
        return coincideCategoria && coincideEntidad;
    });

    // Filtrar historial para line chart
    let historialFiltrado = historialDatosDashboard;
    if (bancoFiltro !== 'todas') {
        historialFiltrado = historialDatosDashboard.filter(h => h.banco === bancoFiltro);
    }
    if (entidadFiltro !== 'todas') {
        historialFiltrado = historialFiltrado.filter(h => h.tipo_entidad === entidadFiltro);
    }
    if (rangoDias !== 'all') {
        const dias = parseInt(rangoDias);
        const fechaLimite = new Date();
        fechaLimite.setDate(fechaLimite.getDate() - dias);
        historialFiltrado = historialFiltrado.filter(h => {
            const f = new Date(h.fecha_registro + 'T00:00:00');
            return f >= fechaLimite;
        });
    }

    renderizarBarChart(tasasFiltradas);
    renderizarLineChart(historialFiltrado, bancoFiltro);

    document.getElementById('bar-chart-count').textContent = `${tasasFiltradas.length} productos`;
}

function renderizarBarChart(tasas) {
    const ctx = document.getElementById('chart-bar-tasas');
    if (!ctx) return;
    const canvas = ctx.getContext('2d');

    if (chartBarInstance) {
        chartBarInstance.destroy();
        chartBarInstance = null;
    }

    const datos = tasas.length > 0 ? tasas : [];
    const labels = datos.map(t => t.banco);
    const valores = datos.map(t => t.tasa_ea);
    const colores = datos.map((t, i) => {
        const tipo = t.tipo_entidad || '';
        if (tipo === 'Cooperativa') return 'rgba(239, 68, 68, 0.7)';
        if (tipo === 'Nubanco') return 'rgba(245, 158, 11, 0.7)';
        return 'rgba(59, 130, 246, 0.7)';
    });
    const bordes = datos.map((t, i) => {
        const tipo = t.tipo_entidad || '';
        if (tipo === 'Cooperativa') return '#ef4444';
        if (tipo === 'Nubanco') return '#f59e0b';
        return '#3b82f6';
    });
    const usura = indicadoresUsuraDashboard['tasa_usura_consumo_ordinario']
        || indicadoresUsuraDashboard['tasa_usura_consumo']
        || 28.79;

    chartBarInstance = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Tasa E.A. (%)',
                data: valores,
                backgroundColor: colores,
                borderColor: bordes,
                borderWidth: 1.5,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, elements) => {
                if (elements.length > 0) {
                    const idx = elements[0].index;
                    const banco = labels[idx];
                    const select = document.getElementById('filtro-banco-dash');
                    if (select) {
                        select.value = banco;
                        aplicarFiltrosDashboard();
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            const t = datos[context.dataIndex];
                            return ` ${t.tipo_entidad || ''}\n Producto: ${t.producto || ''}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af', maxRotation: 45 }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#9ca3af',
                        callback: function(value) { return value.toFixed(1) + '%'; }
                    },
                    suggestedMax: Math.ceil(usura * 1.1)
                }
            }
        }
    });
}

function renderizarLineChart(historial, bancoFiltro) {
    const ctx = document.getElementById('chart-line-historial');
    if (!ctx) return;
    const canvas = ctx.getContext('2d');

    if (chartLineInstance) {
        chartLineInstance.destroy();
        chartLineInstance = null;
    }

    const fechas = [...new Set(historial.map(h => h.fecha_registro))].sort();
    const bancos = bancoFiltro !== 'todas'
        ? [bancoFiltro]
        : [...new Set(historial.map(h => h.banco))];

    if (fechas.length === 0 || bancos.length === 0) {
        chartLineInstance = new Chart(canvas, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#9ca3af', font: { family: 'Inter' } } }
                }
            }
        });
        document.getElementById('line-chart-count').textContent = '0 bancos';
        return;
    }

    const datasets = bancos.map((banco, index) => {
        const datosBanco = historial.filter(h => h.banco === banco);
        const data = fechas.map(f => {
            const r = datosBanco.find(d => d.fecha_registro === f);
            return r ? r.tasa_ea : null;
        });
        const color = obtenerColorBanco(banco, index);
        return {
            label: banco,
            data: data,
            borderColor: color,
            backgroundColor: color + '22',
            borderWidth: bancoFiltro !== 'todas' ? 4 : 3,
            tension: 0.3,
            fill: false,
            pointRadius: bancoFiltro !== 'todas' ? 5 : 3,
            pointHoverRadius: 7
        };
    });

    document.getElementById('line-chart-count').textContent = `${bancos.length} banco(s)`;

    chartLineInstance = new Chart(canvas, {
        type: 'line',
        data: { labels: fechas, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#9ca3af', font: { family: 'Inter', size: 11 } }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af' }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#9ca3af',
                        callback: function(value) { return value.toFixed(1) + '%'; }
                    }
                }
            }
        }
    });
}

function renderizarUsuraChart(histUsura) {
    const ctx = document.getElementById('chart-usura-historial');
    if (!ctx) return;
    const canvas = ctx.getContext('2d');

    if (chartUsuraInstance) {
        chartUsuraInstance.destroy();
        chartUsuraInstance = null;
    }

    const nombres = [...new Set(histUsura.map(h => h.nombre))].filter(n => n.startsWith('tasa_usura_'));
    if (nombres.length === 0) {
        chartUsuraInstance = new Chart(canvas, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: { responsive: true, maintainAspectRatio: false }
        });
        return;
    }

    const fechas = [...new Set(histUsura.map(h => h.fecha_consulta))].sort();

    const coloresUsura = [
        '#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6',
        '#ec4899', '#14b8a6', '#f97316', '#84cc16'
    ];

    const datasets = nombres.map((nombre, idx) => {
        const datos = histUsura.filter(h => h.nombre === nombre);
        const data = fechas.map(f => {
            const r = datos.find(d => d.fecha_consulta === f);
            return r ? r.valor : null;
        });
        const etiqueta = nombre
            .replace('tasa_usura_', '')
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
        return {
            label: etiqueta,
            data: data,
            borderColor: coloresUsura[idx % coloresUsura.length],
            backgroundColor: coloresUsura[idx % coloresUsura.length] + '22',
            borderWidth: 2,
            tension: 0.3,
            fill: false,
            pointRadius: 3
        };
    });

    chartUsuraInstance = new Chart(canvas, {
        type: 'line',
        data: { labels: fechas, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#9ca3af', font: { family: 'Inter', size: 11 } }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af' }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: {
                        color: '#9ca3af',
                        callback: function(value) { return value.toFixed(1) + '%'; }
                    }
                }
            }
        }
    });
}

function exportarHistorialTasas() {
    const datos = historialDatosDashboard;
    if (!datos || datos.length === 0) return;
    const columnas = [
        { campo: "fecha_registro", titulo: "Fecha" },
        { campo: "banco", titulo: "Banco" },
        { campo: "tipo_entidad", titulo: "Tipo Entidad" },
        { campo: "producto", titulo: "Producto" },
        { campo: "tasa_ea", titulo: "Tasa E.A. (%)" },
        { campo: "tasa_mv", titulo: "Tasa M.V. (%)" }
    ];
    descargarCSV(datos, columnas, "historial_tasas_bancarias");
}

function exportarHistorialUsura() {
    const datos = historialUsuraDashboard;
    if (!datos || datos.length === 0) return;
    const columnas = [
        { campo: "nombre", titulo: "Indicador" },
        { campo: "valor", titulo: "Valor (%)" },
        { campo: "fecha_consulta", titulo: "Fecha Consulta" },
        { campo: "fecha_vigencia_inicio", titulo: "Vigencia Desde" },
        { campo: "fecha_vigencia_fin", titulo: "Vigencia Hasta" },
        { campo: "fuente", titulo: "Fuente" }
    ];
    descargarCSV(datos, columnas, "historial_tasas_usura");
}

// ============================================
// AUTENTICACIÓN GOOGLE
// ============================================

async function inicializarAuth() {
    const usuario = await verificarSesion();
    if (usuario && usuario.autenticado) {
        mostrarUsuario(usuario);
        if (!usuario.accepted_terms) {
            mostrarTerminos();
        }
    }
}

async function verificarSesion() {
    try {
        const resp = await fetch('/api/auth/me');
        return await resp.json();
    } catch (e) {
        return { autenticado: false };
    }
}

function mostrarUsuario(usuario) {
    const btn = document.querySelector('.g_id_signin');
    const menu = document.getElementById('user-menu');
    if (btn) btn.style.display = 'none';
    if (menu) {
        menu.style.display = 'flex';
        const avatar = document.getElementById('user-avatar');
        const name = document.getElementById('user-name-display');
        if (avatar) avatar.src = usuario.avatar || '';
        if (name) name.textContent = usuario.nombre || usuario.email || '';
    }
}

async function handleGoogleCredential(response) {
    try {
        const resp = await fetch('/api/auth/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential: response.credential })
        });
        const data = await resp.json();
        if (data.error) {
            console.error('Error auth:', data.error);
            return;
        }
        mostrarUsuario(data);
        if (!data.accepted_terms) {
            mostrarTerminos();
        }
    } catch (e) {
        console.error('Error al autenticar:', e);
    }
}

async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        const btn = document.querySelector('.g_id_signin');
        const menu = document.getElementById('user-menu');
        if (btn) btn.style.display = '';
        if (menu) menu.style.display = 'none';
    } catch (e) {
        console.error('Error al cerrar sesión:', e);
    }
}

function mostrarTerminos() {
    const modal = document.getElementById('terms-modal');
    if (modal) modal.style.display = 'flex';
}

async function aceptarTerminos() {
    try {
        const resp = await fetch('/api/auth/aceptar-terminos', { method: 'POST' });
        const data = await resp.json();
        if (data.status === 'ok') {
            document.getElementById('terms-modal').style.display = 'none';
        }
    } catch (e) {
        console.error('Error al aceptar términos:', e);
    }
}

function renderizarSyncStatus(syncData) {
    const icon = document.getElementById('sync-icon');
    const text = document.getElementById('sync-text');
    if (!icon || !text) return;

    if (syncData.estado === 'SUCCESS') {
        icon.textContent = '\u2705';
        text.textContent = `\u00daltima sincronizaci\u00f3n: ${syncData.fecha_ejecucion} | ${syncData.registros_procesados} registro(s) procesado(s)`;
    } else if (syncData.estado === 'FAILED') {
        icon.textContent = '\u274c';
        text.textContent = `\u00daltima sincronizaci\u00f3n fall\u00f3: ${syncData.fecha_ejecucion} | ${syncData.detalles || ''}`;
    } else {
        icon.textContent = '\u2139\ufe0f';
        text.textContent = 'Sin sincronizaciones previas. Ejecute python scripts/run_etl.py';
    }
}

// Menú responsive
function inicializarMenu() {
    const toggle = document.getElementById('menu-toggle');
    const nav = document.getElementById('nav-links');
    const userArea = document.getElementById('user-area');
    if (!toggle || !nav) return;

    toggle.addEventListener('click', function(e) {
        e.stopPropagation();
        this.classList.toggle('open');
        nav.classList.toggle('open');
        if (userArea) userArea.classList.toggle('open');
    });

    document.addEventListener('click', function(e) {
        if (!toggle.contains(e.target) && !nav.contains(e.target)) {
            toggle.classList.remove('open');
            nav.classList.remove('open');
            if (userArea) userArea.classList.remove('open');
        }
    });
}

document.addEventListener('DOMContentLoaded', inicializarMenu);

// Alternar visibilidad de columnas en tabla comparativa
function toggleCol(n) {
    const table = document.getElementById('tabla-tasas');
    if (!table) return;
    const btns = document.querySelectorAll('.col-toggle[data-col="' + n + '"]');
    const ths = table.querySelectorAll('thead tr th:nth-child(' + n + ')');
    const tds = table.querySelectorAll('tbody tr td:nth-child(' + n + ')');

    ths.forEach(el => el.classList.toggle('hidden-col'));
    tds.forEach(el => el.classList.toggle('hidden-col'));
    btns.forEach(el => el.classList.toggle('active'));
}

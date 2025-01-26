// Configuración global de SweetAlert2
const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true
});

// Funciones para mostrar mensajes
// -------------------------------
function mostrarExito(mensaje) {
    Toast.fire({
        icon: 'success',
        title: mensaje
    });
}

function mostrarError(mensaje) {
    Toast.fire({
        icon: 'error',
        title: mensaje
    });
}

function mostrarAdvertencia(mensaje) {
    Toast.fire({
        icon: 'warning',
        title: mensaje
    });
}

function mostrarInfo(mensaje) {
    Toast.fire({
        icon: 'info',
        title: mensaje
    });
}

// Función para confirmar acciones
function confirmarAccion(titulo, mensaje) {
    return Swal.fire({
        title: titulo,
        text: mensaje,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#004884',
        cancelButtonColor: '#dc3545',
        confirmButtonText: 'Confirmar',
        cancelButtonText: 'Cancelar'
    });
}

// Funciones para validación de formularios
// ----------------------------------------
function validarCamposRequeridos(formulario) {
    let camposValidos = true;
    const camposRequeridos = formulario.querySelectorAll('[required]');
    
    camposRequeridos.forEach(campo => {
        if (!campo.value.trim()) {
            campo.classList.add('is-invalid');
            camposValidos = false;
        } else {
            campo.classList.remove('is-invalid');
        }
    });
    
    return camposValidos;
}

// Funciones para formateo de números
// -----------------------------------
function formatearNumero(numero) {
    return new Intl.NumberFormat('es-CO').format(numero);
}

// Funciones para validación de documentos
// ----------------------------------------
function validarDocumento(documento) {
    return /^\d{5,12}$/.test(documento);
}

// Funciones para validación de correos electrónicos
// ------------------------------------------------
function validarEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Funciones para validación de números de teléfono
// -----------------------------------------------
function validarTelefono(telefono) {
    return /^\d{10}$/.test(telefono);
}

// Funciones para limpieza de formularios
// ---------------------------------------
function limpiarFormulario(formulario) {
    formulario.reset();
    const camposInvalidos = formulario.querySelectorAll('.is-invalid');
    camposInvalidos.forEach(campo => campo.classList.remove('is-invalid'));
}

// Funciones para manejo de botones
// ---------------------------------
function deshabilitarBoton(boton, texto = 'Procesando...') {
    boton.disabled = true;
    boton.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${texto}`;
}

function habilitarBoton(boton, textoOriginal) {
    boton.disabled = false;
    boton.innerHTML = textoOriginal;
}

// Funciones para manejo de errores de fetch
// ------------------------------------------
function manejarErrorFetch(error) {
    console.error('Error:', error);
    mostrarError('Ha ocurrido un error. Por favor, inténtalo de nuevo más tarde.');
}

// Funciones para conversión de formularios a objetos
// -------------------------------------------------
function formToObject(formulario) {
    const formData = new FormData(formulario);
    const objeto = {};
    for (let [key, value] of formData.entries()) {
        objeto[key] = value;
    }
    return objeto;
}

// Event Listeners globales
// -------------------------
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar tooltips de Bootstrap
    $('[data-toggle="tooltip"]').tooltip();

    // Inicializar popovers de Bootstrap
    $('[data-toggle="popover"]').popover();

    // Manejar cierre de alertas
    document.querySelectorAll('.alert .close').forEach(button => {
        button.addEventListener('click', function() {
            this.closest('.alert').remove();
        });
    });

    // Validación de campos en tiempo real
    document.querySelectorAll('input[required], select[required], textarea[required]').forEach(campo => {
        campo.addEventListener('blur', function() {
            if (!this.value.trim()) {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid');
            }
        });
    });
});

// Función para inicializar la aplicación
function init() {
    console.log('Aplicación inicializada');
    // Aquí puedes añadir más lógica de inicialización
}

// Llamar a la función init al cargar la página
window.onload = init;

// Funciones para estudiantes
// -------------------------
const EstudiantesManager = {
    modificar: function (form, callback) {
        const $form = $(form);
        const $row = $form.closest('tr');
        const datos = {
            estudiante_id: $form.find('input[name="estudiante_id"]').val(),
            numero_documento: $row.find('input[name="numero_documento"]').val(),
            nombre: $row.find('input[name="nombre"]').val()
        };

        $.ajax({
            url: '/modificar_estudiante',
            type: 'POST',
            data: datos,
            success: function (response) {
                if (response.success) {
                    mostrarExito('Estudiante modificado exitosamente');
                    if (callback) callback(response);
                } else {
                    mostrarError(response.message);
                }
            },
            error: function (xhr) {
                mostrarError('Error al modificar estudiante: ' + (xhr.responseJSON?.message || 'Error desconocido'));
            }
        });
    },

    eliminar: function (form, callback) {
        const $form = $(form);
        const $row = $form.closest('tr');

        if (confirmarAccion('Eliminar estudiante', '¿Está seguro de que desea eliminar este estudiante?').then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: '/eliminar_estudiante',
                    type: 'POST',
                    data: $form.serialize(),
                    success: function (response) {
                        if (response.success) {
                            mostrarExito('Estudiante eliminado exitosamente');
                            if (callback) callback($row);
                        } else {
                            mostrarError(response.message);
                        }
                    },
                    error: function () {
                        mostrarError('Error al eliminar estudiante');
                    }
                });
            }
        }));
    }
};

// Funciones para asignación de mesas
// -----------------------------------
const MesasManager = {
    toggleGrados: function (sedeId) {
        const gradosDiv = $(`#grados-${sedeId}`);
        $('.grados-container').not(gradosDiv).slideUp();
        gradosDiv.slideToggle();
    },

    eliminarAsignacion: function (id) {
        confirmarAccion('Eliminar asignación', '¿Está seguro de que desea eliminar esta asignación?').then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: `/eliminar_asignacion/${id}`,
                    type: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    success: function (response) {
                        if (response.success) {
                            $.get('/asignar_mesas', function (data) {
                                var sedeId = response.sede_id;

                                // Actualizar la lista de grados de la sede específica
                                var $newGradosContainer = $(data).find(`#grados-${sedeId}`);
                                $(`#grados-${sedeId}`).html($newGradosContainer.html());

                                // Actualizar la tabla de asignaciones
                                var $newAsignaciones = $(data).find(`.asignacion-sede-card[data-sede-id="${sedeId}"] .asignaciones-table tbody`);
                                $(`.asignacion-sede-card[data-sede-id="${sedeId}"] .asignaciones-table tbody`).html($newAsignaciones.html());

                                // Actualizar la sección de resumen
                                $('.resumen-accordion').html($(data).find('.resumen-accordion').html());

                                // Actualizar la sección de selección de sede
                                var $newSedeList = $(data).find('.sede-list');
                                $('.sede-list').html($newSedeList.html());

                                // Mantener visible el contenedor de grados si estaba visible
                                if ($(`#grados-${sedeId}`).is(':visible')) {
                                    $(`#grados-${sedeId}`).show();
                                }

                                // Reinicializar eventos
                                MesasManager.initEvents();

                                mostrarExito('Asignación eliminada correctamente');
                            });
                        } else {
                            mostrarError('Error al eliminar la asignación');
                        }
                    },
                    error: function (xhr) {
                        mostrarError('Error al eliminar la asignación');
                    }
                });
            }
        });
    },

    toggleAsignaciones: function (element) {
        const $link = $(element);
        const $content = $link.closest('.asignacion-sede-card').find('.asignacion-sede-content');
        const $icon = $link.find('i');

        // Prevenir que el evento se propague
        event.preventDefault();
        event.stopPropagation();

        // Cierra otros paneles
        $('.asignacion-sede-content').not($content).slideUp();
        $('.asignacion-sede-link').not($link).removeClass('active');
        $('.asignacion-sede-link i').not($icon).removeClass('fa-chevron-up').addClass('fa-chevron-down');

        // Toggle del panel actual
        $content.stop(true, true).slideToggle();  // Agregamos stop() para prevenir animaciones en cola
        $link.toggleClass('active');
        $icon.toggleClass('fa-chevron-down fa-chevron-up');
    },

    toggleResumen: function (element) {
        const $link = $(element);
        const $content = $link.closest('.resumen-sede-card').find('.resumen-sede-content');
        const $icon = $link.find('i');

        // Prevenir que el evento se propague
        event.preventDefault();
        event.stopPropagation();

        // Cierra otros paneles
        $('.resumen-sede-content').not($content).slideUp();
        $('.resumen-sede-link').not($link).removeClass('active');
        $('.resumen-sede-link i').not($icon).removeClass('fa-chevron-up').addClass('fa-chevron-down');

        // Toggle del panel actual
        $content.stop(true, true).slideToggle();  // Agregamos stop() para prevenir animaciones en cola
        $link.toggleClass('active');
        $icon.toggleClass('fa-chevron-down fa-chevron-up');
    },

    initEvents: function () {
        // Eventos para los radio buttons
        $('.mesa-radio').off('change').on('change', function (e) {
            e.stopPropagation();
            var gradoSeccion = $(this).data('grado-seccion');
            var mesaNumero = $(this).val();
            var sedeId = $(this).data('sede-id');
            var $row = $(this).closest('tr');
            var $gradosContainer = $(`#grados-${sedeId}`);
            var $sedeItem = $gradosContainer.closest('.sede-item');

            // Deshabilitar todos los radio buttons en la fila
            $row.find('input[type="radio"]').prop('disabled', true);

            $.ajax({
                url: '/asignar_mesas',
                type: 'POST',
                data: {
                    grado_seccion: gradoSeccion,
                    mesa_numero: mesaNumero,
                    sede_id: sedeId
                },
                success: function (response) {
                    if (response.success) {
                        $.get('/asignar_mesas', function (data) {
                            // Actualizar la sección de asignaciones
                            $('.asignaciones-accordion').html($(data).find('.asignaciones-accordion').html());
                            // Actualizar la sección de resumen
                            $('.resumen-accordion').html($(data).find('.resumen-accordion').html());

                            // Verificar si hay más grados sin asignar en esta sede
                            var $newGradosContainer = $(data).find(`#grados-${sedeId}`);
                            var hayMasGrados = $newGradosContainer.find('tr').length > 0;

                            if (hayMasGrados) {
                                // Si hay más grados, actualizar solo el contenedor de grados
                                $gradosContainer.html($newGradosContainer.html());
                            } else {
                                // Si no hay más grados, ocultar y eliminar el contenedor de grados
                                $gradosContainer.slideUp(400, function () {
                                    $sedeItem.remove();
                                });
                            }

                            // Reinicializar eventos
                            MesasManager.initEvents();

                            mostrarExito('Asignación realizada correctamente');
                        });
                    } else {
                        mostrarError('Error al realizar la asignación');
                        // Reactivar los radio buttons si hay error
                        $row.find('input[type="radio"]').prop('disabled', false);
                    }
                },
                error: function () {
                    mostrarError('Error al realizar la asignación');
                    // Reactivar los radio buttons si hay error
                    $row.find('input[type="radio"]').prop('disabled', false);
                }
            });
        });

        // Eventos para los enlaces de sede
        $('.sede-link').off('click').on('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            MesasManager.toggleGrados($(this).data('sede-id'));
        });

        // Eventos para los botones de eliminar
        $('.btn-eliminar-asignacion').off('click').on('click', function () {
            MesasManager.eliminarAsignacion($(this).data('id'));
        });

        // Eventos para los enlaces de asignaciones
        $('.asignacion-sede-link').off('click').on('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            MesasManager.toggleAsignaciones(this);
        });

        // Eventos para los enlaces de resumen
        $('.resumen-sede-link').off('click').on('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            MesasManager.toggleResumen(this);
        });
    }
};

// Inicialización cuando el documento está listo
$(document).ready(function () {
    MesasManager.initEvents();
});

// Manejo de carga masiva de testigos
// -----------------------------------
const CargaMasivaManager = {
    init: function() {
        // Actualizar el nombre del archivo seleccionado
        $('.custom-file-input').on('change', function() {
            let fileName = $(this).val().split('\\').pop();
            $(this).next('.custom-file-label').html(fileName || 'Seleccionar archivo');
        });

        // Descargar plantilla CSV
        $('#descargarPlantilla').on('click', function(e) {
            e.preventDefault();
            CargaMasivaManager.descargarPlantilla();
        });

        // Manejar el envío del formulario
        $('#formCargaMasiva').on('submit', function(e) {
            e.preventDefault();
            CargaMasivaManager.procesarArchivo(this);
        });
    },

    descargarPlantilla: function() {
        const headers = [
            'numero_documento',
            'nombre_completo',
            'telefono',
            'email',
            'sede',
            'mesas',
            'representacion'
        ];
        
        const csvContent = headers.join(',') + '\\n' +
            '1234567890,Juan Pérez,3001234567,juan@ejemplo.com,Sede Principal,1;2;3,Partido A\\n' +
            '0987654321,María López,3109876543,maria@ejemplo.com,Sede Norte,4;5,Partido B';

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.setAttribute('download', 'plantilla_testigos.csv');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },

    procesarArchivo: function(form) {
        const fileInput = form.querySelector('input[type="file"]');
        const file = fileInput.files[0];

        if (!file) {
            mostrarError('Por favor seleccione un archivo CSV');
            return;
        }

        if (file.size > 5 * 1024 * 1024) { // 5MB
            mostrarError('El archivo es demasiado grande. El tamaño máximo es 5MB');
            return;
        }

        const formData = new FormData(form);
        const $submitBtn = $(form).find('button[type="submit"]');
        const originalBtnText = $submitBtn.html();

        // Mostrar progreso
        $(form).closest('.card').find('.upload-progress').show();
        
        // Deshabilitar botón y mostrar spinner
        deshabilitarBoton($submitBtn[0], 'Procesando...');

        $.ajax({
            url: '/testigos/cargar-csv',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            xhr: function() {
                const xhr = new XMLHttpRequest();
                xhr.upload.addEventListener('progress', function(e) {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        $('.progress-bar').width(percent + '%').text(percent + '%');
                    }
                });
                return xhr;
            },
            success: function(response) {
                if (response.success) {
                    mostrarExito('Archivo procesado exitosamente');
                    
                    // Mostrar resultados
                    let resultadosHTML = `
                        <div class="card mt-3">
                            <div class="card-header">
                                <h5 class="mb-0">Resultados de la carga</h5>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="stats-card bg-success text-white">
                                            <h6>Registros exitosos</h6>
                                            <h3>${response.exitosos}</h3>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="stats-card bg-warning text-dark">
                                            <h6>Registros con advertencias</h6>
                                            <h3>${response.advertencias}</h3>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="stats-card bg-danger text-white">
                                            <h6>Registros fallidos</h6>
                                            <h3>${response.errores}</h3>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    // Mostrar detalles de errores si existen
                    if (response.detalles && response.detalles.length > 0) {
                        resultadosHTML += `
                            <div class="card mt-3">
                                <div class="card-header">
                                    <h5 class="mb-0">Detalles de errores</h5>
                                </div>
                                <div class="list-group list-group-flush">
                                    ${response.detalles.map(detalle => `
                                        <div class="list-group-item">
                                            <div class="d-flex w-100 justify-content-between">
                                                <h6 class="mb-1">Fila ${detalle.fila}</h6>
                                                <small class="text-${detalle.tipo === 'error' ? 'danger' : 'warning'}">
                                                    ${detalle.tipo === 'error' ? 'Error' : 'Advertencia'}
                                                </small>
                                            </div>
                                            <p class="mb-1">${detalle.mensaje}</p>
                                            <small>Documento: ${detalle.documento || 'N/A'}</small>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `;
                    }

                    $('.upload-results').html(resultadosHTML).show();
                    
                    // Actualizar estadísticas si es necesario
                    if (typeof cargarEstadisticas === 'function') {
                        cargarEstadisticas();
                    }
                } else {
                    mostrarError(response.message || 'Error al procesar el archivo');
                }
            },
            error: function(xhr) {
                mostrarError('Error al procesar el archivo: ' + (xhr.responseJSON?.message || 'Error desconocido'));
            },
            complete: function() {
                // Ocultar progreso y restaurar botón
                $('.upload-progress').hide();
                $('.progress-bar').width('0%').text('0%');
                habilitarBoton($submitBtn[0], originalBtnText);
                
                // Limpiar input file
                fileInput.value = '';
                $(fileInput).next('.custom-file-label').html('Seleccionar archivo');
            }
        });
    }
};

// Inicializar el manejador de carga masiva cuando el documento esté listo
document.addEventListener('DOMContentLoaded', function() {
    CargaMasivaManager.init();
});

// Otras funciones globales que necesites...

function deshabilitarFormulario(selector, deshabilitar) {
    const $elemento = $(selector);

    // Deshabilitar inputs y botones
    $elemento.find('input, button, select, .sede-link, .asignacion-sede-link').prop('disabled', deshabilitar);

    if (deshabilitar) {
        $elemento.addClass('form-disabled');
        // Agregar clase visual de deshabilitado
        $elemento.css('opacity', '0.7');
        $elemento.find('.mesa-radio').css('pointer-events', 'none');
    } else {
        $elemento.removeClass('form-disabled');
        $elemento.css('opacity', '1');
        $elemento.find('.mesa-radio').css('pointer-events', 'auto');
    }
}

const TestigosManager = {
    registrar: function (form, callback) {
        const $form = $(form);
        const datos = {
            nombre: $form.find('input[name="nombre"]').val(),
            numero_documento: $form.find('input[name="numero_documento"]').val(),
            correo: $form.find('input[name="correo"]').val(),
            telefono: $form.find('input[name="telefono"]').val()
        };

        $.ajax({
            url: '/registrar_testigo',
            type: 'POST',
            data: datos,
            success: function (response) {
                if (response.success) {
                    mostrarExito('Testigo registrado exitosamente');
                    if (callback) callback(response);
                } else {
                    mostrarError(response.message);
                }
            },
            error: function (xhr) {
                mostrarError('Error al registrar testigo: ' + (xhr.responseJSON?.message || 'Error desconocido'));
            }
        });
    }
};
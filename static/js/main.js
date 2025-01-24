// Configuración global de Toastr
$(document).ready(function () {
    toastr.options = {
        "closeButton": true,
        "debug": false,
        "newestOnTop": false,
        "progressBar": true,
        "positionClass": "toast-top-right",
        "preventDuplicates": false,
        "onclick": null,
        "showDuration": "300",
        "hideDuration": "1000",
        "timeOut": "5000",
        "extendedTimeOut": "1000",
        "showEasing": "swing",
        "hideEasing": "linear",
        "showMethod": "fadeIn",
        "hideMethod": "fadeOut"
    };

    // Verificar estado de configuración usando el objeto appConfig
    if (typeof appConfig !== 'undefined' && appConfig.configuracionFinalizada) {
        // Deshabilitar todos los botones de edición
        $('.btn-editar, .btn-eliminar, .btn-agregar').prop('disabled', true);
        // Ocultar formularios de registro
        $('.form-registro').hide();
        // Mostrar mensaje si no está visible
        if (!$('#sistema-bloqueado-alert').is(':visible')) {
            const alertHTML = `
                <div class="alert alert-warning" id="sistema-bloqueado-alert">
                    <i class="fas fa-lock"></i> Configuración Inicial bloqueada.
                    ${appConfig.fechaFinalizacion ?
                    `La configuración fue finalizada el ${appConfig.fechaFinalizacion}` :
                    ''}
                </div>
            `;
            $('.container').prepend(alertHTML);
        }
    }
});

// Función global para mostrar mensajes
function mostrarMensaje(mensaje, tipo) {
    switch (tipo) {
        case 'success':
            toastr.success(mensaje);
            break;
        case 'error':
        case 'danger':
            toastr.error(mensaje);
            break;
        case 'warning':
            toastr.warning(mensaje);
            break;
        case 'info':
            toastr.info(mensaje);
            break;
    }
}

// Funciones para estudiantes
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
                    mostrarMensaje('Estudiante modificado exitosamente', 'success');
                    if (callback) callback(response);
                } else {
                    mostrarMensaje(response.message, 'error');
                }
            },
            error: function (xhr) {
                mostrarMensaje('Error al modificar estudiante: ' + (xhr.responseJSON?.message || 'Error desconocido'), 'error');
            }
        });
    },

    eliminar: function (form, callback) {
        const $form = $(form);
        const $row = $form.closest('tr');

        if (confirm('¿Está seguro de que desea eliminar este estudiante?')) {
            $.ajax({
                url: '/eliminar_estudiante',
                type: 'POST',
                data: $form.serialize(),
                success: function (response) {
                    if (response.success) {
                        mostrarMensaje('Estudiante eliminado exitosamente', 'success');
                        if (callback) callback($row);
                    } else {
                        mostrarMensaje(response.message, 'error');
                    }
                },
                error: function () {
                    mostrarMensaje('Error al eliminar estudiante', 'error');
                }
            });
        }
    }
};

// Funciones para asignación de mesas
const MesasManager = {
    toggleGrados: function (sedeId) {
        const gradosDiv = $(`#grados-${sedeId}`);
        $('.grados-container').not(gradosDiv).slideUp();
        gradosDiv.slideToggle();
    },

    eliminarAsignacion: function (id) {
        if (confirm('¿Está seguro de que desea eliminar esta asignación?')) {
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

                            mostrarMensaje('Asignación eliminada correctamente', 'success');
                        });
                    } else {
                        mostrarMensaje('Error al eliminar la asignación', 'error');
                    }
                },
                error: function (xhr) {
                    mostrarMensaje('Error al eliminar la asignación', 'error');
                }
            });
        }
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

                            mostrarMensaje('Asignación realizada correctamente', 'success');
                        });
                    } else {
                        mostrarMensaje('Error al realizar la asignación', 'error');
                        // Reactivar los radio buttons si hay error
                        $row.find('input[type="radio"]').prop('disabled', false);
                    }
                },
                error: function () {
                    mostrarMensaje('Error al realizar la asignación', 'error');
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
                    mostrarMensaje('Testigo registrado exitosamente', 'success');
                    if (callback) callback(response);
                } else {
                    mostrarMensaje(response.message, 'error');
                }
            },
            error: function (xhr) {
                mostrarMensaje('Error al registrar testigo: ' + (xhr.responseJSON?.message || 'Error desconocido'), 'error');
            }
        });
    }
};
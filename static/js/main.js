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

    seleccionarMesa: function (gradoSeccion, mesaNumero, sedeId) {
        if (confirm(`¿Desea asignar la mesa ${mesaNumero} al grado ${gradoSeccion}?`)) {
            const form = $('#asignarMesaForm');
            form.find('[name="grado_seccion"]').val(`${gradoSeccion}|${sedeId}`);
            form.find('[name="mesa_numero"]').val(mesaNumero);
            form.submit();
        }
    },

    eliminarAsignacion: function (id) {
        if (confirm('¿Está seguro de que desea eliminar esta asignación?')) {
            $.ajax({
                url: `/eliminar_asignacion/${id}`,
                type: 'POST',
                success: function (response) {
                    if (response.success) {
                        // Actualizar solo las secciones necesarias
                        $.get('/asignar_mesas', function (data) {
                            // Actualizar la sección de asignaciones
                            $('.asignaciones-accordion').html($(data).find('.asignaciones-accordion').html());
                            // Actualizar la sección de resumen
                            $('.resumen-accordion').html($(data).find('.resumen-accordion').html());
                            // Actualizar la lista de grados disponibles
                            $('.sede-list').html($(data).find('.sede-list').html());

                            // Reinicializar los eventos
                            MesasManager.initEvents();

                            mostrarMensaje('Asignación eliminada correctamente', 'success');
                        });
                    } else {
                        mostrarMensaje('Error al eliminar la asignación', 'error');
                    }
                },
                error: function () {
                    mostrarMensaje('Error al eliminar la asignación', 'error');
                }
            });
        }
    },

    toggleAsignaciones: function (element) {
        const $link = $(element);
        const $content = $link.closest('.asignacion-sede-card').find('.asignacion-sede-content');
        const $icon = $link.find('i');

        // Cierra otros paneles
        $('.asignacion-sede-content').not($content).slideUp();
        $('.asignacion-sede-link').not($link).removeClass('active');
        $('.asignacion-sede-link i').not($icon).removeClass('fa-chevron-up').addClass('fa-chevron-down');

        // Toggle del panel actual
        $content.slideToggle();
        $link.toggleClass('active');
        $icon.toggleClass('fa-chevron-down fa-chevron-up');
    },

    toggleResumen: function (element) {
        const $link = $(element);
        const $content = $link.closest('.resumen-sede-card').find('.resumen-sede-content');
        const $icon = $link.find('i');

        // Cierra otros paneles
        $('.resumen-sede-content').not($content).slideUp();
        $('.resumen-sede-link').not($link).removeClass('active');
        $('.resumen-sede-link i').not($icon).removeClass('fa-chevron-up').addClass('fa-chevron-down');

        // Toggle del panel actual
        $content.slideToggle();
        $link.toggleClass('active');
        $icon.toggleClass('fa-chevron-down fa-chevron-up');
    },

    asignarMesa: function (gradoSeccion, mesaNumero, sedeId) {
        if (confirm(`¿Desea asignar la mesa ${mesaNumero} al grado ${gradoSeccion}?`)) {
            $.ajax({
                url: '/asignar_mesas',
                type: 'POST',
                data: {
                    grado_seccion: `${gradoSeccion}|${sedeId}`,
                    mesa_numero: mesaNumero
                },
                success: function (response) {
                    if (response.success) {
                        // Actualizar solo las secciones necesarias
                        $.get('/asignar_mesas', function (data) {
                            // Actualizar la sección de asignaciones
                            $('.asignaciones-accordion').html($(data).find('.asignaciones-accordion').html());
                            // Actualizar la sección de resumen
                            $('.resumen-accordion').html($(data).find('.resumen-accordion').html());
                            // Actualizar la lista de grados disponibles
                            $('.sede-list').html($(data).find('.sede-list').html());

                            // Reinicializar los eventos
                            MesasManager.initEvents();

                            mostrarMensaje('Asignación realizada correctamente', 'success');
                        });
                    } else {
                        mostrarMensaje('Error al realizar la asignación', 'error');
                    }
                },
                error: function () {
                    mostrarMensaje('Error al realizar la asignación', 'error');
                }
            });
        }
    },

    initEvents: function () {
        // Eventos para el acordeón de asignaciones
        $('.asignacion-sede-link').on('click', function (e) {
            e.preventDefault();
            MesasManager.toggleAsignaciones(this);
        });

        // Eventos para el acordeón de resumen
        $('.resumen-sede-link').on('click', function (e) {
            e.preventDefault();
            MesasManager.toggleResumen(this);
        });

        // Eventos para los radio buttons
        $('.mesa-radio').on('change', function () {
            const $this = $(this);
            const gradoSeccion = $this.data('grado-seccion');
            const mesaNumero = $this.val();
            const sedeId = $this.data('sede-id');
            MesasManager.asignarMesa(gradoSeccion, mesaNumero, sedeId);
        });

        // Eventos para eliminar asignaciones
        $('.btn-eliminar-asignacion').on('click', function () {
            const id = $(this).data('id');
            MesasManager.eliminarAsignacion(id);
        });

        // Eventos para mostrar/ocultar grados
        $('.sede-link').on('click', function (e) {
            e.preventDefault();
            const sedeId = $(this).data('sede-id');
            MesasManager.toggleGrados(sedeId);
        });
    }
};

// Inicialización cuando el documento está listo
$(document).ready(function () {
    MesasManager.initEvents();
});

// Agregar a las funciones existentes
function checkConfiguracionBloqueada() {
    $.get('/check_configuracion_estado', function (response) {
        if (response.bloqueada) {
            // Deshabilitar todos los botones de edición
            $('.btn-editar, .btn-eliminar, .btn-agregar').prop('disabled', true);
            // Ocultar formularios de registro
            $('.form-registro').hide();
            // Mostrar mensaje de sistema bloqueado
            $('#sistema-bloqueado-alert').show();
        }
    });
}

$(document).ready(function () {
    checkConfiguracionBloqueada();
});

// Otras funciones globales que necesites...
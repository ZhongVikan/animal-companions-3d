extends Control
class_name ArenaTouchControls

const MOVE_CENTER := Vector2(126, 582)
const THROW_CENTER := Vector2(1159, 576)
const BLOCK_CENTER := Vector2(1028, 628)
const MOVE_RADIUS := 77.0
const THROW_RADIUS := 60.0
const BLOCK_RADIUS := 48.0

var movement := Vector2.ZERO
var _move_finger := -1
var _throw_finger := -1
var _block_finger := -1
var _throw_queued := false
var _active := false

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	hide()
	set_process_input(false)

func set_active(active: bool) -> void:
	if _active == active:
		return
	_active = active
	visible = active
	set_process_input(active)
	if not active:
		_reset()

func consume_throw() -> bool:
	var requested := _throw_queued or _throw_finger >= 0
	_throw_queued = false
	return requested

func is_block_held() -> bool:
	return _block_finger >= 0

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		_reset()

func _reset() -> void:
	movement = Vector2.ZERO
	_move_finger = -1
	_throw_finger = -1
	_block_finger = -1
	_throw_queued = false
	queue_redraw()

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed and not event.canceled:
			_start_touch(event.index, event.position)
		else:
			_end_touch(event.index)
	elif event is InputEventScreenDrag and event.index == _move_finger:
		_update_movement(event.position)
		get_viewport().set_input_as_handled()

func _start_touch(index: int, point: Vector2) -> void:
	if _move_finger < 0 and point.distance_to(MOVE_CENTER) <= MOVE_RADIUS + 24.0:
		_move_finger = index
		_update_movement(point)
	elif _throw_finger < 0 and point.distance_to(THROW_CENTER) <= THROW_RADIUS + 12.0:
		_throw_finger = index
		_throw_queued = true
	elif _block_finger < 0 and point.distance_to(BLOCK_CENTER) <= BLOCK_RADIUS + 12.0:
		_block_finger = index
	else:
		return
	queue_redraw()
	get_viewport().set_input_as_handled()

func _end_touch(index: int) -> void:
	if index == _move_finger:
		_move_finger = -1
		movement = Vector2.ZERO
	elif index == _throw_finger:
		_throw_finger = -1
	elif index == _block_finger:
		_block_finger = -1
	else:
		return
	queue_redraw()
	get_viewport().set_input_as_handled()

func _update_movement(point: Vector2) -> void:
	var offset := point - MOVE_CENTER
	movement = Vector2.ZERO if offset.length() < 9.0 else (offset / 53.0).limit_length()
	queue_redraw()

func _draw() -> void:
	draw_circle(MOVE_CENTER, MOVE_RADIUS, Color("#17112bd9"), true, -1, true)
	draw_arc(MOVE_CENTER, MOVE_RADIUS, 0.0, TAU, 64, Color("#a889e0"), 2.5, true)
	var knob_center := MOVE_CENTER + movement * 44.0
	draw_circle(knob_center, 28.0, Color("#8661c7"), true, -1, true)
	draw_arc(knob_center, 28.0, 0.0, TAU, 48, Color("#ddc8ff"), 2.5, true)
	_draw_action(THROW_CENTER, THROW_RADIUS, "投掷", Color("#ffd88d"), _throw_finger >= 0)
	_draw_action(BLOCK_CENTER, BLOCK_RADIUS, "格挡", Color("#ddc8ff"), _block_finger >= 0)

func _draw_action(center: Vector2, radius: float, caption: String, ink: Color, held: bool) -> void:
	var fill := ink if held else Color("#17112beb")
	var text_color := Color("#221731") if held else ink
	draw_circle(center, radius, fill, true, -1, true)
	draw_arc(center, radius, 0.0, TAU, 64, ink, 2.5, true)
	var font := get_theme_default_font()
	var font_size := 26
	var text_size := font.get_string_size(caption, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size)
	var baseline := (font.get_ascent(font_size) - font.get_descent(font_size)) / 2.0
	draw_string(font, center + Vector2(-text_size.x / 2.0, baseline), caption, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, text_color)

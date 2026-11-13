extends CharacterBody3D
class_name ArenaPlayer

signal throw_requested(player: ArenaPlayer, origin: Vector3, direction: Vector3)
signal eliminated(player: ArenaPlayer)

var player_id: int = 0
var player_name: String = "P1"
var model_path: String = ""
var player_color: Color = Color.WHITE
var is_human: bool = false
var control_prefix: String = "p1"
var alive: bool = true
var blocking: bool = false
var throw_cooldown: float = 0.0
var block_cooldown: float = 0.0
var hit_flash: float = 0.0
var spawn_position: Vector3
var ai_move := Vector2.ZERO
var ai_aim := Vector3.FORWARD
var ai_wants_throw := false
var ai_wants_block := false
var model_root: Node3D
var body_mesh: MeshInstance3D

const SPEED := 4.5
const THROW_COOLDOWN := 0.72
const BLOCK_WINDOW := 0.42

func setup(id: int, title: String, asset_path: String, tint: Color, human: bool, prefix: String, spawn: Vector3) -> void:
	player_id = id
	player_name = title
	model_path = asset_path
	player_color = tint
	is_human = human
	control_prefix = prefix
	spawn_position = spawn
	position = spawn
	_setup_collision()
	_setup_model()

func _setup_collision() -> void:
	var shape_node := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = 0.38
	shape.height = 1.48
	shape_node.shape = shape
	shape_node.position.y = 0.74
	add_child(shape_node)

func _setup_model() -> void:
	if not ResourceLoader.exists(model_path):
		return
	var packed := load(model_path) as PackedScene
	if packed == null:
		return
	model_root = packed.instantiate()
	model_root.name = "CharacterModel"
	model_root.scale = Vector3.ONE * 0.72
	# The exported models use +Z as their front; the game faces -Z by default.
	model_root.rotation.y = PI
	add_child(model_root)
	# A colored halo makes player ownership readable even with the plush atlas.
	var halo := MeshInstance3D.new()
	var ring := TorusMesh.new()
	ring.inner_radius = 0.45
	ring.outer_radius = 0.49
	var halo_mat := StandardMaterial3D.new()
	halo_mat.albedo_color = Color(player_color, 0.78)
	halo_mat.emission_enabled = true
	halo_mat.emission = player_color * 0.45
	halo_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ring.material = halo_mat
	halo.mesh = ring
	halo.position.y = 0.018
	halo.rotation.x = -PI / 2.0
	add_child(halo)

func reset_for_round(spawn: Vector3) -> void:
	spawn_position = spawn
	global_position = spawn
	velocity = Vector3.ZERO
	alive = true
	blocking = false
	# Give the first round a readable opening before CPU volleys begin.
	throw_cooldown = 1.15
	block_cooldown = 0.0
	hit_flash = 0.0
	visible = true

func eliminate() -> void:
	if not alive:
		return
	alive = false
	blocking = false
	velocity = Vector3.ZERO
	visible = false
	eliminated.emit(self)

func set_ai_intent(move: Vector2, aim: Vector3, wants_throw: bool, wants_block: bool) -> void:
	ai_move = move
	ai_aim = aim
	ai_wants_throw = wants_throw
	ai_wants_block = wants_block

func _human_move() -> Vector2:
	return Input.get_vector(control_prefix + "_left", control_prefix + "_right", control_prefix + "_up", control_prefix + "_down")

func _process_input() -> void:
	if not is_human:
		return
	ai_move = _human_move()
	if ai_move.length_squared() > 0.01:
		ai_aim = Vector3(ai_move.x, 0.0, ai_move.y).normalized()
	ai_wants_throw = Input.is_action_just_pressed(control_prefix + "_throw")
	ai_wants_block = Input.is_action_pressed(control_prefix + "_block")

func tick(delta: float, arena_half_extents: Vector2) -> void:
	if not alive:
		return
	_process_input()
	throw_cooldown = maxf(0.0, throw_cooldown - delta)
	block_cooldown = maxf(0.0, block_cooldown - delta)
	hit_flash = maxf(0.0, hit_flash - delta)
	blocking = ai_wants_block and block_cooldown <= 0.0
	var desired := ai_move
	if desired.length_squared() > 1.0:
		desired = desired.normalized()
	velocity = Vector3(desired.x, 0.0, desired.y) * SPEED
	move_and_slide()
	global_position.x = clampf(global_position.x, -arena_half_extents.x, arena_half_extents.x)
	global_position.z = clampf(global_position.z, -arena_half_extents.y, arena_half_extents.y)
	if ai_aim.length_squared() > 0.01:
		var target_angle := atan2(ai_aim.x, ai_aim.z)
		rotation.y = lerp_angle(rotation.y, target_angle + PI, minf(1.0, delta * 12.0))
	if ai_wants_throw and throw_cooldown <= 0.0 and not blocking:
		throw_cooldown = THROW_COOLDOWN
		var direction := ai_aim
		if direction.length_squared() < 0.01:
			direction = Vector3.FORWARD
		direction.y = 0.0
		direction = direction.normalized()
		throw_requested.emit(self, global_position + Vector3.UP * 0.86, direction)
		ai_wants_throw = false

func consume_block() -> void:
	blocking = false
	block_cooldown = 0.15


extends Node3D
class_name ArenaPie

var owner_id: int = -1
var velocity := Vector3.ZERO
var age := 0.0
var bounces := 0
var active := true

const SPEED := 9.0
const MAX_AGE := 4.6
const MAX_BOUNCES := 4

func setup(source_id: int, origin: Vector3, direction: Vector3, tint: Color) -> void:
	owner_id = source_id
	position = origin
	velocity = direction.normalized() * SPEED
	var mesh_instance := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.17
	sphere.height = 0.34
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.98, 0.76, 0.53)
	material.roughness = 0.42
	material.emission_enabled = true
	material.emission = Color(0.18, 0.07, 0.025)
	sphere.material = material
	mesh_instance.mesh = sphere
	add_child(mesh_instance)
	var glow := OmniLight3D.new()
	glow.light_color = tint
	glow.light_energy = 0.45
	glow.omni_range = 1.2
	add_child(glow)

func tick(delta: float, bounds: Vector2) -> void:
	if not active:
		return
	age += delta
	global_position += velocity * delta
	rotation.x += delta * 9.0
	rotation.z += delta * 7.0
	if absf(global_position.x) > bounds.x:
		global_position.x = signf(global_position.x) * bounds.x
		velocity.x *= -1.0
		bounces += 1
	if absf(global_position.z) > bounds.y:
		global_position.z = signf(global_position.z) * bounds.y
		velocity.z *= -1.0
		bounces += 1
	if age > MAX_AGE or bounces > MAX_BOUNCES:
		active = false


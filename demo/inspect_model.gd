extends SceneTree

func _init() -> void:
	for path in ["res://models/glb/01_giraffe.glb", "res://models/glb/02_rabbit.glb"]:
		var packed := load(path) as PackedScene
		print("MODEL", path, " packed=", packed != null)
		if packed == null:
			continue
		var root := packed.instantiate()
		print("ROOT", root.name, " children=", root.get_child_count(), " visible=", root.visible)
		_print_nodes(root, "  ")
		root.queue_free()
	quit()

func _print_nodes(node: Node, indent: String) -> void:
	for child in node.get_children():
		var line := indent + child.name + " type=" + child.get_class() + " visible=" + str(child.visible if child is CanvasItem or child is Node3D else true)
		if child is MeshInstance3D:
			line += " aabb=" + str(child.get_aabb()) + " mesh=" + str(child.mesh != null)
		print(line)
		_print_nodes(child, indent + "  ")

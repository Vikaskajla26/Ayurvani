import onnxruntime as ort

model_path = "models/sanskrit-vits-int8.onnx"
print("Loading model:", model_path)
session = ort.InferenceSession(model_path)

print("\n--- Inputs ---")
for input_node in session.get_inputs():
    print(f"Name: {input_node.name}")
    print(f"Type: {input_node.type}")
    print(f"Shape: {input_node.shape}")

print("\n--- Outputs ---")
for output_node in session.get_outputs():
    print(f"Name: {output_node.name}")
    print(f"Type: {output_node.type}")
    print(f"Shape: {output_node.shape}")

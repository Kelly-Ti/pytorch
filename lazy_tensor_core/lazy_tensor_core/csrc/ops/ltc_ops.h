#pragma once

#include <torch/csrc/lazy/ts_backend/ts_node.h>

#include <mutex>
#include <string>

namespace torch_lazy_tensors {
namespace ir {
namespace ops {

class OpKindWrapper {
 public:
  OpKindWrapper(const char* name) : name_(name) {}

  const torch::lazy::OpKind& operator*() const { return get(); }

  operator torch::lazy::OpKind() const { return get(); }

 private:
  const torch::lazy::OpKind& get() const {
    std::call_once(once_,
                   [this]() { op_kind_ = torch::lazy::OpKind::Get(name_); });
    return op_kind_;
  }

  const char* name_;
  mutable torch::lazy::OpKind op_kind_;
  mutable std::once_flag once_;
};

extern const OpKindWrapper ltc_all_to_all;
extern const OpKindWrapper ltc_as_strided_view_update;
extern const OpKindWrapper ltc_cast;
extern const OpKindWrapper ltc_collective_permute;
extern const OpKindWrapper ltc_cross_replica_sum;
extern const OpKindWrapper ltc_device_data;
extern const OpKindWrapper ltc_diagonal_view_update;
extern const OpKindWrapper ltc_generic_slice;
extern const OpKindWrapper ltc_get_dimensions_size;
extern const OpKindWrapper ltc_moving_average;
extern const OpKindWrapper ltc_nms;
extern const OpKindWrapper ltc_not_supported;
extern const OpKindWrapper ltc_replication_pad;
extern const OpKindWrapper ltc_replication_pad_backward;
extern const OpKindWrapper ltc_select;
extern const OpKindWrapper ltc_tensor_data;
extern const OpKindWrapper ltc_unselect;
extern const OpKindWrapper ltc_update_slice;

}  // namespace ops
}  // namespace ir
}  // namespace torch_lazy_tensors
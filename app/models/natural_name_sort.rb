module NaturalNameSort
  module_function

  def sort(records, attribute = :name)
    records.to_a.each_with_index.sort_by do |(record, index)|
      value = record.public_send(attribute).to_s

      [
        key_for(value),
        value.downcase,
        value,
        index
      ]
    end.map(&:first)
  end

  def key_for(value)
    value.to_s.scan(/\d+|\D+/).map do |segment|
      if segment.match?(/\A\d+\z/)
        [ 0, segment.to_i ]
      else
        [ 1, segment.downcase ]
      end
    end
  end
end
